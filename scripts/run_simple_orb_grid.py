#!/usr/bin/env python3
"""Barrido de parámetros del ORB clásico (sin absorción CVD, ver
src/simple_orb.py) sobre los 6 meses reales de QQQ (Databento), con un
split honesto de fechas: la primera mitad del historial ("train") se usa
para elegir la mejor combinación de parámetros por Sortino, y la segunda
mitad ("test") -- que el proceso de selección NUNCA ve -- se usa solo para
reportar el resultado final. Esto evita reportar un número sobreajustado
al total de los 6 meses (el mismo error que se evitó explícitamente al
descartar el filtro de bandas de desviación estándar semanal).

El sizing usa `max_leverage=1.0` (sin margen: la posición nunca excede el
equity disponible) -- un stop muy ajustado (p.ej. anclado en la mecha real
de la vela de rompimiento, en modo "fade") puede pedir arriesgar el 1% de
equity con una posición nocional de decenas de veces el equity si no se
limita; con el tope, el riesgo real de esos trades queda por debajo del
1% nominal, y el R-multiple se recalcula sobre el riesgo real. Ver
src/simple_orb.py.

Uso:
    python scripts/run_simple_orb_grid.py                  # 1m, 2m, 3m, 5m
    python scripts/run_simple_orb_grid.py --interval 1m
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

OR_MINUTES_GRID = [15, 25, 30, 35, 45]
SL_MODE_GRID = ["or_opposite", "liquidity"]
TP_R_GRID = [1.5, 2.0, 3.0]
TREND_FILTER_GRID = [False, True]
DIRECTION_MODE_GRID = ["breakout", "fade"]
MAX_LEVERAGE = 1.0  # sin margen -- la posición nunca excede el equity disponible

MIN_TRAIN_TRADES = 10  # combinaciones con menos trades en train no son fiables para elegir parámetros


def _split_train_test(df):
    dates = sorted(set(df.index.date))
    split_date = dates[len(dates) // 2]
    train = df[df.index.date < split_date]
    test = df[df.index.date >= split_date]
    return train, test, split_date


def _grid_combos():
    for or_minutes, sl_mode, tp_r, trend, direction_mode in product(
        OR_MINUTES_GRID, SL_MODE_GRID, TP_R_GRID, TREND_FILTER_GRID, DIRECTION_MODE_GRID
    ):
        yield dict(
            or_minutes=or_minutes, sl_mode=sl_mode, tp_r_multiple=tp_r,
            trend_filter_enabled=trend, direction_mode=direction_mode,
        )


def run_for_interval(label: str, path: str, outdir: Path):
    df = load_csv(path, tz="America/New_York")
    train_df, test_df, split_date = _split_train_test(df)
    n_train_days = len(set(train_df.index.date))
    n_test_days = len(set(test_df.index.date))
    print(f"\n=== {label}: {n_train_days} días train (< {split_date}), "
          f"{n_test_days} días test (>= {split_date}) ===")

    base_cfg = SimpleORBConfig(
        session_open="09:30", session_close="16:00", session_only=True, max_leverage=MAX_LEVERAGE
    )

    train_rows = []
    best = None  # (sortino, profit_factor, combo, metrics)
    for combo in _grid_combos():
        cfg = dataclasses.replace(base_cfg, **combo)
        trades, equity_curve = run_backtest_simple(train_df, cfg)
        metrics = compute_metrics(trades, equity_curve)
        train_rows.append({**combo, **metrics})

        if metrics["num_trades"] < MIN_TRAIN_TRADES:
            continue
        pf = metrics["profit_factor"] if metrics["profit_factor"] not in (None,) else 0.0
        pf = pf if pf == pf else 0.0  # nan -> 0.0
        key = (metrics["sortino_ratio"], pf)
        if best is None or key > (best[0], best[1]):
            best = (metrics["sortino_ratio"], pf, combo, metrics)

    train_rows.sort(key=lambda r: r["sortino_ratio"], reverse=True)

    if best is None:
        print(f"  Ninguna combinación alcanzó {MIN_TRAIN_TRADES} trades en train -> sin selección posible.")
        return {
            "interval": label, "split_date": str(split_date),
            "n_train_days": n_train_days, "n_test_days": n_test_days,
            "train_top5": train_rows[:5], "selected_combo": None, "test_metrics": None,
        }

    _, _, best_combo, best_train_metrics = best
    print(f"  Mejor combo en TRAIN (Sortino): {best_combo}")
    print(f"    train: trades={best_train_metrics['num_trades']}, "
          f"sortino={best_train_metrics['sortino_ratio']}, pf={best_train_metrics['profit_factor']}, "
          f"return={best_train_metrics['total_return_pct']}%")

    # Evaluación honesta: el combo elegido en train, corrido en test (fuera de muestra)
    cfg_test = dataclasses.replace(base_cfg, **best_combo)
    test_trades, test_equity_curve = run_backtest_simple(test_df, cfg_test)
    test_metrics = compute_metrics(test_trades, test_equity_curve)
    print(f"    test (fuera de muestra): trades={test_metrics['num_trades']}, "
          f"sortino={test_metrics['sortino_ratio']}, pf={test_metrics['profit_factor']}, "
          f"return={test_metrics['total_return_pct']}%")

    return {
        "interval": label, "split_date": str(split_date),
        "n_train_days": n_train_days, "n_test_days": n_test_days,
        "train_top5": train_rows[:5], "selected_combo": best_combo,
        "train_metrics": best_train_metrics, "test_metrics": test_metrics,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", default=None, choices=list(SOURCES.keys()),
                         help="Un solo intervalo; default: corre 1m y 5m")
    parser.add_argument("--outdir", default="results/simple_orb_grid")
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
        results[label] = run_for_interval(label, path, outdir)

    with open(outdir / "simple_orb_grid_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    # ---------------- Reporte markdown ----------------
    md_path = outdir / "simple_orb_grid_report.md"
    with open(md_path, "w") as f:
        f.write("# ORB clásico (sin absorción CVD): barrido de parámetros con split train/test\n\n")
        f.write(
            "Split honesto por fecha: la primera mitad de los ~6 meses reales de QQQ se usa "
            "para elegir la mejor combinación de parámetros por Sortino ratio (train); la "
            "segunda mitad se evalúa SOLO con esa combinación ya elegida, sin volver a buscar "
            "parámetros (test, fuera de muestra). Esto es lo mínimo para no reportar un número "
            "inflado por sobreajuste al dataset completo.\n\n"
            f"Grid: OR={OR_MINUTES_GRID} min, SL={SL_MODE_GRID}, TP={TP_R_GRID}R, "
            f"filtro de tendencia={TREND_FILTER_GRID}, dirección={DIRECTION_MODE_GRID} "
            f"({len(OR_MINUTES_GRID) * len(SL_MODE_GRID) * len(TP_R_GRID) * len(TREND_FILTER_GRID) * len(DIRECTION_MODE_GRID)} "
            f"combinaciones), mínimo {MIN_TRAIN_TRADES} trades en train para poder elegirse. "
            f"Sizing con `max_leverage={MAX_LEVERAGE}` (sin margen: la posición nunca excede el "
            "equity disponible, incluso si el SL queda muy ajustado -- ver src/simple_orb.py).\n\n"
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
            f.write("Top 5 combos en train por Sortino:\n\n")
            top_cols = ["or_minutes", "sl_mode", "tp_r_multiple", "trend_filter_enabled", "direction_mode",
                        "num_trades", "sortino_ratio", "profit_factor", "total_return_pct"]
            f.write("| " + " | ".join(top_cols) + " |\n")
            f.write("|" + "---|" * len(top_cols) + "\n")
            for row in r["train_top5"]:
                f.write("| " + " | ".join(str(row.get(c, "")) for c in top_cols) + " |\n")
            f.write("\n")

    print(f"\nReporte guardado en {outdir}/: simple_orb_grid_report.md, simple_orb_grid_results.json")


if __name__ == "__main__":
    main()
