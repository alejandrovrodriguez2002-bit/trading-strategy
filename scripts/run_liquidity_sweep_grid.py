#!/usr/bin/env python3
"""Barrido del "barrido de liquidez" (`range_source="prev_session"` en
src/simple_orb.py): el rompimiento se mide contra el high/low de TODA la
sesión de trading ANTERIOR (PDH/PDL -- un pool de liquidez clásico de
ICT/SMC), no contra el rango de apertura de hoy. Dos modos de take profit:

- "opposite_extreme": el lado del rango anterior que NO se rompió (barre
  el PDH, apunta al PDL, y viceversa) -- los "highs and lows de la sesión
  anterior... como precio objetivo" pedidos.
- "poc": el Punto de Control (POC) de la sesión anterior -- el nivel de
  precio con más volumen acumulado, como objetivo alternativo/más cercano.

Mismo split honesto train/test por fecha que scripts/run_simple_orb_grid.py
(la primera mitad del historial elige parámetros por Sortino; la segunda
mitad, nunca vista, evalúa esa combinación ya fija) y mismo tope de
apalancamiento (`max_leverage=1.0`, sin margen) para no reportar un
resultado que dependa de una posición nocional irrealista.

Uso:
    python scripts/run_liquidity_sweep_grid.py                  # 1m, 2m, 3m, 5m
    python scripts/run_liquidity_sweep_grid.py --interval 5m
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
from src.simple_orb import SimpleORBConfig, run_backtest_simple  # noqa: E402

SOURCES = {
    "1m": "data/databento_QQQ_1m_candles.csv",
    "2m": "data/databento_QQQ_2m_candles.csv",
    "3m": "data/databento_QQQ_3m_candles.csv",
    "5m": "data/databento_QQQ_5m_candles.csv",
}

TP_MODE_GRID = ["opposite_extreme", "poc"]
SL_MODE_GRID = ["or_opposite", "liquidity"]
DIRECTION_MODE_GRID = ["fade", "breakout"]
TREND_FILTER_GRID = [False, True]
MAX_LEVERAGE = 1.0  # sin margen -- la posición nunca excede el equity disponible

MIN_TRAIN_TRADES = 10  # combinaciones con menos trades en train no son fiables para elegir parámetros


def _split_train_test(df):
    dates = sorted(set(df.index.date))
    split_date = dates[len(dates) // 2]
    train = df[df.index.date < split_date]
    test = df[df.index.date >= split_date]
    return train, test, split_date


def _grid_combos():
    for tp_mode, sl_mode, direction_mode, trend in product(
        TP_MODE_GRID, SL_MODE_GRID, DIRECTION_MODE_GRID, TREND_FILTER_GRID
    ):
        yield dict(
            tp_mode=tp_mode, sl_mode=sl_mode,
            direction_mode=direction_mode, trend_filter_enabled=trend,
        )


def run_for_interval(label: str, path: str):
    df = load_csv(path, tz="America/New_York")
    train_df, test_df, split_date = _split_train_test(df)
    n_train_days = len(set(train_df.index.date))
    n_test_days = len(set(test_df.index.date))
    print(f"\n=== {label}: {n_train_days} días train (< {split_date}), "
          f"{n_test_days} días test (>= {split_date}) ===")

    base_cfg = SimpleORBConfig(
        session_open="09:30", session_close="16:00", session_only=True,
        range_source="prev_session", volume_filter_enabled=False, max_leverage=MAX_LEVERAGE,
    )

    train_rows = []
    best = None
    for combo in _grid_combos():
        cfg = dataclasses.replace(base_cfg, **combo)
        trades, equity_curve = run_backtest_simple(train_df, cfg)
        metrics = compute_metrics(trades, equity_curve)
        train_rows.append({**combo, **metrics})

        if metrics["num_trades"] < MIN_TRAIN_TRADES:
            continue
        pf = metrics["profit_factor"]
        pf = pf if (pf == pf and pf not in (None,)) else 0.0  # nan/None -> 0.0
        key = (metrics["sortino_ratio"], pf)
        if best is None or key > (best[0], best[1]):
            best = (metrics["sortino_ratio"], pf, combo, metrics)

    train_rows.sort(key=lambda r: r["sortino_ratio"], reverse=True)

    if best is None:
        print(f"  Ninguna combinación alcanzó {MIN_TRAIN_TRADES} trades en train -> sin selección posible.")
        return {
            "interval": label, "split_date": str(split_date),
            "n_train_days": n_train_days, "n_test_days": n_test_days,
            "train_top": train_rows[:8], "selected_combo": None, "test_metrics": None,
        }

    _, _, best_combo, best_train_metrics = best
    print(f"  Mejor combo en TRAIN (Sortino): {best_combo}")
    print(f"    train: trades={best_train_metrics['num_trades']}, "
          f"sortino={best_train_metrics['sortino_ratio']}, pf={best_train_metrics['profit_factor']}, "
          f"return={best_train_metrics['total_return_pct']}%")

    cfg_test = dataclasses.replace(base_cfg, **best_combo)
    test_trades, test_equity_curve = run_backtest_simple(test_df, cfg_test)
    test_metrics = compute_metrics(test_trades, test_equity_curve)
    print(f"    test (fuera de muestra): trades={test_metrics['num_trades']}, "
          f"sortino={test_metrics['sortino_ratio']}, pf={test_metrics['profit_factor']}, "
          f"return={test_metrics['total_return_pct']}%")

    return {
        "interval": label, "split_date": str(split_date),
        "n_train_days": n_train_days, "n_test_days": n_test_days,
        "train_top": train_rows[:8], "selected_combo": best_combo,
        "train_metrics": best_train_metrics, "test_metrics": test_metrics,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", default=None, choices=list(SOURCES.keys()),
                         help="Un solo intervalo; default: corre 1m, 2m, 3m, 5m")
    parser.add_argument("--outdir", default="results/liquidity_sweep_grid")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    intervals = [args.interval] if args.interval else ["1m", "2m", "3m", "5m"]
    results = {}
    for label in intervals:
        path = SOURCES[label]
        if not Path(path).exists():
            print(f"[{label}] archivo no encontrado, se omite: {path}")
            continue
        results[label] = run_for_interval(label, path)

    with open(outdir / "liquidity_sweep_grid_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    md_path = outdir / "liquidity_sweep_grid_report.md"
    with open(md_path, "w") as f:
        f.write("# Barrido de liquidez (PDH/PDL) con objetivo en el lado opuesto y en el POC\n\n")
        f.write(
            "`range_source=\"prev_session\"`: el rompimiento se mide contra el high/low de TODA "
            "la sesión de trading anterior (no el rango de apertura de hoy). `tp_mode=\"opposite_extreme\"` "
            "apunta al lado del rango anterior que NO se rompió; `tp_mode=\"poc\"` apunta al Punto de "
            "Control (nivel de más volumen) de la sesión anterior. Mismo split honesto train/test por "
            "fecha que la variante fade original: la primera mitad de los ~6 meses reales de QQQ elige "
            "la mejor combinación por Sortino (train); la segunda mitad, nunca vista, evalúa esa "
            "combinación ya fija (test). Sizing con `max_leverage=1.0` (sin margen).\n\n"
            f"Grid: TP={TP_MODE_GRID}, SL={SL_MODE_GRID}, dirección={DIRECTION_MODE_GRID}, "
            f"filtro de tendencia={TREND_FILTER_GRID} "
            f"({len(TP_MODE_GRID) * len(SL_MODE_GRID) * len(DIRECTION_MODE_GRID) * len(TREND_FILTER_GRID)} "
            f"combinaciones), mínimo {MIN_TRAIN_TRADES} trades en train para poder elegirse.\n\n"
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
            top_cols = ["tp_mode", "sl_mode", "direction_mode", "trend_filter_enabled",
                        "num_trades", "sortino_ratio", "profit_factor", "total_return_pct"]
            f.write("| " + " | ".join(top_cols) + " |\n")
            f.write("|" + "---|" * len(top_cols) + "\n")
            for row in r["train_top"]:
                f.write("| " + " | ".join(str(row.get(c, "")) for c in top_cols) + " |\n")
            f.write("\n")

    print(f"\nReporte guardado en {outdir}/: liquidity_sweep_grid_report.md, liquidity_sweep_grid_results.json")


if __name__ == "__main__":
    main()
