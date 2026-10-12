#!/usr/bin/env python3
"""Estrategia pedida: marcar el rango COMPLETO de la sesión de Asia
(19:00-04:00 ET, 9h) y operar la REACCIÓN (reversión) cuando la sesión de
Londres toca esos niveles -- un concepto de liquidez ICT/SMC clásico
("barrida del rango asiático durante Londres").

Usa `src/session_zone.py` con la zona `asia_range_london_reaction`
(zone_start=19:00, zone_end=04:00, search_hours=8.0 -- desde que Asia
cierra hasta que Londres cierra a las 12:00). Datos: NQ real (CME Globex,
~180 días, el mismo dataset usado para "Zonas de valor").

Barre `tp_mode` x `sl_mode` x `direction_mode` (12 combinaciones) con el
mismo split honesto train/test por fecha del resto del proyecto, en
5m y 15m.

Uso:
    python scripts/run_asia_london_reaction_grid.py
    python scripts/run_asia_london_reaction_grid.py --interval 5m
"""
import argparse
import dataclasses
import json
import sys
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import load_csv  # noqa: E402
from src.metrics import compute_metrics  # noqa: E402
from src.session_zone import SessionZoneConfig, ZONES, run_backtest_zone  # noqa: E402

SOURCES = {
    "5m": "data/databento_NQ_c_0_5m_candles.csv",
    "15m": "data/databento_NQ_c_0_15m_candles.csv",
}

ZONE_PARAMS = ZONES["asia_range_london_reaction"]

TP_MODE_GRID = ["r_multiple", "opposite_extreme", "poc"]
TP_R_GRID = [1.0, 1.5, 2.0, 3.0]  # solo aplica cuando tp_mode == "r_multiple"
SL_MODE_GRID = ["or_opposite", "liquidity"]
DIRECTION_MODE_GRID = ["fade", "breakout"]
MAX_LEVERAGE = 1.0  # sin margen, misma convención del resto del proyecto

MIN_TRAIN_TRADES = 10


def _split_train_test(df):
    dates = sorted(set(df.index.date))
    split_date = dates[len(dates) // 2]
    train = df[df.index.date < split_date]
    test = df[df.index.date >= split_date]
    return train, test, split_date


def _grid_combos():
    for tp_mode, sl_mode, direction_mode in product(TP_MODE_GRID, SL_MODE_GRID, DIRECTION_MODE_GRID):
        if tp_mode == "r_multiple":
            for tp_r in TP_R_GRID:
                yield dict(tp_mode=tp_mode, sl_mode=sl_mode, direction_mode=direction_mode, tp_r_multiple=tp_r)
        else:
            yield dict(tp_mode=tp_mode, sl_mode=sl_mode, direction_mode=direction_mode)


def run_for_interval(label: str, path: str):
    df = load_csv(path, tz="America/New_York")
    train_df, test_df, split_date = _split_train_test(df)
    n_train_days = len(set(train_df.index.date))
    n_test_days = len(set(test_df.index.date))
    print(f"\n=== {label}: {n_train_days} días train (< {split_date}), "
          f"{n_test_days} días test (>= {split_date}) ===")

    base_cfg = SessionZoneConfig(max_leverage=MAX_LEVERAGE, **ZONE_PARAMS)

    train_rows = []
    best = None
    for combo in _grid_combos():
        cfg = dataclasses.replace(base_cfg, **combo)
        trades, ec = run_backtest_zone(train_df, cfg)
        metrics = compute_metrics(trades, ec)
        train_rows.append({**combo, **metrics})

        if metrics["num_trades"] < MIN_TRAIN_TRADES:
            continue
        pf = metrics["profit_factor"]
        pf = pf if (pf == pf and pf not in (None,)) else 0.0
        key = (metrics["sortino_ratio"], pf)
        if best is None or key > (best[0], best[1]):
            best = (metrics["sortino_ratio"], pf, combo, metrics)

    train_rows.sort(key=lambda r: r["sortino_ratio"], reverse=True)

    if best is None:
        print(f"  Ninguna combinación alcanzó {MIN_TRAIN_TRADES} trades en train -> sin selección posible.")
        return {
            "interval": label, "split_date": str(split_date),
            "n_train_days": n_train_days, "n_test_days": n_test_days,
            "train_top": train_rows[:12], "selected_combo": None, "test_metrics": None,
        }

    _, _, best_combo, best_train_metrics = best
    print(f"  Mejor combo en TRAIN (Sortino): {best_combo}")
    print(f"    train: trades={best_train_metrics['num_trades']}, "
          f"sortino={best_train_metrics['sortino_ratio']}, pf={best_train_metrics['profit_factor']}, "
          f"return={best_train_metrics['total_return_pct']}%")

    cfg_test = dataclasses.replace(base_cfg, **best_combo)
    test_trades, test_ec = run_backtest_zone(test_df, cfg_test)
    test_metrics = compute_metrics(test_trades, test_ec)
    print(f"    test (fuera de muestra): trades={test_metrics['num_trades']}, "
          f"sortino={test_metrics['sortino_ratio']}, pf={test_metrics['profit_factor']}, "
          f"return={test_metrics['total_return_pct']}%")

    return {
        "interval": label, "split_date": str(split_date),
        "n_train_days": n_train_days, "n_test_days": n_test_days,
        "train_top": train_rows[:12], "selected_combo": best_combo,
        "train_metrics": best_train_metrics, "test_metrics": test_metrics,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", default=None, choices=list(SOURCES.keys()))
    parser.add_argument("--outdir", default="results/asia_london_reaction_grid")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    intervals = [args.interval] if args.interval else list(SOURCES.keys())
    results = {}
    for label in intervals:
        path = SOURCES[label]
        if not Path(path).exists():
            print(f"[{label}] archivo no encontrado, se omite: {path}")
            continue
        results[label] = run_for_interval(label, path)

    with open(outdir / "asia_london_reaction_grid_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    md_path = outdir / "asia_london_reaction_grid_report.md"
    with open(md_path, "w") as f:
        f.write("# Reacción al rango de Asia durante Londres (NQ real)\n\n")
        f.write(
            "Se marca el rango COMPLETO de la sesión de Asia (19:00-04:00 ET) y se busca la "
            "reacción (rompimiento de ese high/low) durante la sesión de Londres (desde que "
            "Asia cierra hasta que Londres cierra, 8h). Split honesto por fecha: primera mitad "
            "del historial de NQ como train, segunda mitad (\"test\") nunca usada para elegir "
            "parámetros. Sizing con `max_leverage=1.0` (sin margen).\n\n"
            f"Grid: TP={TP_MODE_GRID} (con TP_R={TP_R_GRID} solo para \"r_multiple\"), "
            f"SL={SL_MODE_GRID}, dirección={DIRECTION_MODE_GRID} "
            f"({len(list(_grid_combos()))} combinaciones), mínimo {MIN_TRAIN_TRADES} trades en "
            "train para poder elegirse.\n\n"
        )
        for label, r in results.items():
            f.write(f"## {label}\n\n")
            f.write(f"- Train: {r['n_train_days']} días (hasta antes de {r['split_date']})\n")
            f.write(f"- Test: {r['n_test_days']} días (desde {r['split_date']}, fuera de muestra)\n\n")
            if r["selected_combo"] is None:
                f.write("Ninguna combinación tuvo suficientes trades en train. Sin resultado.\n\n")
                continue
            f.write(f"**Combo elegido en train:** `{r['selected_combo']}`\n\n")
            cols = ["num_trades", "total_return_pct", "win_rate_pct", "profit_factor",
                    "expectancy_R", "max_drawdown_pct", "sharpe_ratio", "sortino_ratio"]
            f.write("| | " + " | ".join(cols) + " |\n")
            f.write("|---|" + "---|" * len(cols) + "\n")
            f.write("| train (in-sample) | " + " | ".join(str(r["train_metrics"][c]) for c in cols) + " |\n")
            f.write("| test (fuera de muestra) | " + " | ".join(str(r["test_metrics"][c]) for c in cols) + " |\n\n")
            f.write("Todas las combinaciones en train, por Sortino:\n\n")
            top_cols = ["tp_mode", "tp_r_multiple", "sl_mode", "direction_mode",
                        "num_trades", "sortino_ratio", "profit_factor", "total_return_pct"]
            f.write("| " + " | ".join(top_cols) + " |\n")
            f.write("|" + "---|" * len(top_cols) + "\n")
            for row in r["train_top"]:
                f.write("| " + " | ".join(str(row.get(c, "")) for c in top_cols) + " |\n")
            f.write("\n")

    print(f"\nReporte guardado en {outdir}/: asia_london_reaction_grid_report.md, "
          f"asia_london_reaction_grid_results.json")


if __name__ == "__main__":
    main()
