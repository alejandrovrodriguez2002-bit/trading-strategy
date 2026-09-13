#!/usr/bin/env python3
"""Barrido de la ventana de Opening Range (5/10/15/30/60 min) sobre datos
REALES de QQQ (Databento, ~6 meses) o NASDAQ Composite (^IXIC, Yahoo,
historial corto), en vez de los datasets sintéticos.

Corre uno o más CSV (uno por granularidad) con el mismo motor (filtro de
volumen + absorción CVD + SL/TP por swings).

Uso:
    python scripts/run_or_window_sweep_real.py                    # QQQ/Databento, ~6 meses
    python scripts/run_or_window_sweep_real.py --source ixic      # ^IXIC/Yahoo, historial corto
    python scripts/run_or_window_sweep_real.py --csv data/mi_archivo.csv
"""
import argparse
import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.backtest import run_backtest  # noqa: E402
from src.config import Config  # noqa: E402
from src.data import load_csv  # noqa: E402
from src.metrics import compute_metrics  # noqa: E402

OR_MINUTES_LIST = [5, 10, 15, 30, 60]

SOURCES = {
    "qqq": {  # Databento, ~6 meses de historial real
        "1m": "data/databento_QQQ_1m_candles.csv",
        "2m": "data/databento_QQQ_2m_candles.csv",
        "3m": "data/databento_QQQ_3m_candles.csv",
        "5m": "data/databento_QQQ_5m_candles.csv",
        "10m": "data/databento_QQQ_10m_candles.csv",
        "15m": "data/databento_QQQ_15m_candles.csv",
        "30m": "data/databento_QQQ_30m_candles.csv",
        "60m": "data/databento_QQQ_60m_candles.csv",
    },
    "ixic": {  # Yahoo Finance, historial corto (~4-20 días según intervalo)
        "1m": "data/nasdaq_IXIC_1m_candles.csv",
        "2m": "data/nasdaq_IXIC_2m_candles.csv",
        "3m": "data/nasdaq_IXIC_3m_candles.csv",
        "5m": "data/nasdaq_IXIC_5m_candles.csv",
    },
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/strategy_config.yaml")
    parser.add_argument("--source", default="qqq", choices=list(SOURCES.keys()),
                         help="Fuente de datos predefinida (default: qqq = Databento, ~6 meses)")
    parser.add_argument("--csv", default=None, help="Un solo CSV; si se pasa, ignora --source")
    parser.add_argument("--outdir", default=None,
                         help="Default: results/or_window_sweep_real_<source>")
    args = parser.parse_args()

    base_cfg = Config.from_yaml(args.config)
    outdir = Path(args.outdir or f"results/or_window_sweep_real_{args.source}")
    outdir.mkdir(parents=True, exist_ok=True)

    files = {"custom": args.csv} if args.csv else SOURCES[args.source]

    rows = []
    equity_by_combo = {}
    min_days, max_days = None, None

    for label, path in files.items():
        if not Path(path).exists():
            print(f"[{label}] archivo no encontrado, se omite: {path}")
            continue

        df = load_csv(path, tz=base_cfg.timezone)
        n_days = len(set(df.index.date))
        min_days = n_days if min_days is None else min(min_days, n_days)
        max_days = n_days if max_days is None else max(max_days, n_days)
        date_range = f"{df.index.min().date()} -> {df.index.max().date()}"
        print(f"\n=== {label} ({path}): {n_days} días, {date_range} ===")

        for or_minutes in OR_MINUTES_LIST:
            cfg = dataclasses.replace(base_cfg, or_minutes=or_minutes)
            trades, equity_curve = run_backtest(df, cfg)
            metrics = compute_metrics(trades, equity_curve)

            combo_key = f"{label}_OR{or_minutes}"
            equity_by_combo[combo_key] = equity_curve

            row = {"interval": label, "n_days": n_days, "date_range": date_range,
                   "or_minutes": or_minutes, **metrics}
            rows.append(row)
            print(f"  OR={or_minutes:>2}min: {metrics['num_trades']} trades, "
                  f"return={metrics['total_return_pct']}%, sortino={metrics['sortino_ratio']}, "
                  f"profit_factor={metrics['profit_factor']}")

    # ---------------- Tabla comparativa ----------------
    cols = [
        "interval", "n_days", "or_minutes", "num_trades", "total_return_pct", "win_rate_pct",
        "profit_factor", "expectancy_R", "max_drawdown_pct", "sharpe_ratio", "sortino_ratio",
    ]
    md_path = outdir / "or_window_sweep_real_report.md"
    with open(md_path, "w") as f:
        f.write(f"# Barrido de OR (5/10/15/30/60 min) sobre datos REALES ({args.source.upper()})\n\n")
        if min_days is not None and min_days < 40:
            f.write(
                f"⚠️ Historial corto ({min_days}-{max_days} días según intervalo) — el número "
                "de trades por combinación puede ser bajo, así que Sortino/Sharpe pueden no ser "
                "estadísticamente significativos. Esto es una prueba de que el motor corre bien "
                "sobre datos reales y una primera lectura direccional.\n\n"
            )
        else:
            f.write(
                f"Historial real de {min_days}-{max_days} días (~6 meses) — suficiente para una "
                "lectura direccional razonable, aunque sigue siendo un solo instrumento/periodo "
                "de mercado (no reemplaza forward-testing ni walk-forward).\n\n"
            )
        f.write("| " + " | ".join(cols) + " |\n")
        f.write("|" + "---|" * len(cols) + "\n")
        for row in rows:
            f.write("| " + " | ".join(str(row.get(c, "")) for c in cols) + " |\n")

    with open(outdir / "or_window_sweep_real.json", "w") as f:
        json.dump(rows, f, indent=2, default=str)

    # ---------------- Gráfico: equity curves por intervalo ----------------
    intervals = sorted(set(r["interval"] for r in rows))
    fig, axes = plt.subplots(1, len(intervals), figsize=(5 * len(intervals), 4.5), sharey=False)
    if len(intervals) == 1:
        axes = [axes]
    for ax, interval in zip(axes, intervals):
        for or_minutes in OR_MINUTES_LIST:
            key = f"{interval}_OR{or_minutes}"
            if key in equity_by_combo:
                ec = equity_by_combo[key]
                ax.plot(ec.index, ec.values, label=f"OR {or_minutes} min")
        ax.set_title(f"Velas de {interval}", fontsize=9)
        ax.legend(fontsize=7)
        ax.grid(alpha=0.3)
        ax.tick_params(axis="x", labelrotation=30, labelsize=7)
    fig.suptitle(f"Equity curve (datos reales {args.source.upper()}) por ventana de OR e intervalo")
    fig.tight_layout()
    fig.savefig(outdir / "equity_curves_real.png", dpi=140)
    plt.close(fig)

    print(f"\nReporte guardado en {outdir}/: or_window_sweep_real_report.md, "
          f"or_window_sweep_real.json, equity_curves_real.png")


if __name__ == "__main__":
    main()

