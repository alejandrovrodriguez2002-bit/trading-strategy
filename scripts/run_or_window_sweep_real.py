#!/usr/bin/env python3
"""Barrido de la ventana de Opening Range (5/10/15/30/60 min) sobre datos
REALES de NASDAQ Composite (^IXIC), en vez de los datasets sintéticos.

Corre uno o más CSV (uno por granularidad — 1m/2m/3m/5m) con el mismo
motor (filtro de volumen + absorción CVD + SL/TP por swings).

⚠️ El historial real disponible es corto (limitación de Yahoo Finance, no
del código — ver README.md): ~20 días para 2m/5m, ~4 días para 1m/3m. Los
resultados aquí son una prueba de "funciona con datos reales" y una
primera lectura direccional, NO una estimación confiable de rentabilidad
(muy pocos trades para sacar conclusiones estadísticas).

Uso:
    python scripts/run_or_window_sweep_real.py
    python scripts/run_or_window_sweep_real.py --csv data/nasdaq_IXIC_5m_candles.csv
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

DEFAULT_FILES = {
    "1m": "data/nasdaq_IXIC_1m_candles.csv",
    "2m": "data/nasdaq_IXIC_2m_candles.csv",
    "3m": "data/nasdaq_IXIC_3m_candles.csv",
    "5m": "data/nasdaq_IXIC_5m_candles.csv",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/strategy_config.yaml")
    parser.add_argument("--csv", default=None, help="Un solo CSV; si se omite, corre los 4 de DEFAULT_FILES")
    parser.add_argument("--outdir", default="results/or_window_sweep_real")
    args = parser.parse_args()

    base_cfg = Config.from_yaml(args.config)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    files = {"custom": args.csv} if args.csv else DEFAULT_FILES

    rows = []
    equity_by_combo = {}

    for label, path in files.items():
        if not Path(path).exists():
            print(f"[{label}] archivo no encontrado, se omite: {path}")
            continue

        df = load_csv(path, tz=base_cfg.timezone)
        n_days = len(set(df.index.date))
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
        f.write("# Barrido de OR (5/10/15/30/60 min) sobre datos REALES (NASDAQ ^IXIC)\n\n")
        f.write(
            "⚠️ Historial corto por límite de Yahoo Finance en datos intradía "
            "(no del código): ~20 días para 2m/5m, ~4 días para 1m/3m. Con tan "
            "pocos días el número de trades por combinación es muy bajo (a "
            "veces 0-3) — esto es una prueba de que el motor corre bien sobre "
            "datos reales y una primera lectura direccional, **no** una "
            "estimación confiable de rentabilidad ni de Sortino/Sharpe "
            "(estadísticamente poco significativos con tan pocas muestras).\n\n"
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
                ax.plot(ec.index, ec.values, label=f"OR {or_minutes} min", marker="o", markersize=3)
        ax.set_title(f"Velas de {interval}", fontsize=9)
        ax.legend(fontsize=7)
        ax.grid(alpha=0.3)
        ax.tick_params(axis="x", labelrotation=30, labelsize=7)
    fig.suptitle("Equity curve (datos reales NASDAQ ^IXIC) por ventana de OR e intervalo")
    fig.tight_layout()
    fig.savefig(outdir / "equity_curves_real.png", dpi=140)
    plt.close(fig)

    print(f"\nReporte guardado en {outdir}/: or_window_sweep_real_report.md, "
          f"or_window_sweep_real.json, equity_curves_real.png")


if __name__ == "__main__":
    main()
