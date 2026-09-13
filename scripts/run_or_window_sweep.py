#!/usr/bin/env python3
"""Barrido del tamaño del rango de apertura (OR): 5, 10, 15, 30 y 60 minutos,
sobre los 3 datasets sintéticos (A/B/C), dejando todo lo demás igual
(filtro de volumen, confirmación por absorción CVD, gestión de riesgo).

Responde a la pregunta: "¿el minuto exacto donde se marca el high/low de
apertura importa para el resultado?" — no es una estimación de rentabilidad
real, es otra prueba de robustez/sensibilidad de parámetros.

Uso:
    python scripts/run_or_window_sweep.py
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
import numpy as np  # noqa: E402

from src.backtest import run_backtest  # noqa: E402
from src.config import Config  # noqa: E402
from src.metrics import compute_metrics  # noqa: E402
from src.synthetic_datasets import generate_dataset_a, generate_dataset_b, generate_dataset_c  # noqa: E402

DATASETS = {
    "A_tradicional": ("A — Tradicional (GBM+GARCH)", generate_dataset_a),
    "B_soc": ("B — SOC/multifractal", generate_dataset_b),
    "C_regime": ("C — Regime-switching", generate_dataset_c),
}
OR_MINUTES_LIST = [5, 10, 15, 30, 60]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/strategy_config.yaml")
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--outdir", default="results/or_window_sweep")
    args = parser.parse_args()

    base_cfg = Config.from_yaml(args.config)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # generar cada dataset una sola vez (misma serie de precios para las 3 ventanas de OR)
    dfs = {key: gen(months_back=args.months) for key, (_, gen) in DATASETS.items()}

    rows = []
    equity_by_combo = {}

    for or_minutes in OR_MINUTES_LIST:
        cfg = dataclasses.replace(base_cfg, or_minutes=or_minutes)
        for key, (label, _) in DATASETS.items():
            df = dfs[key]
            df_for_bt = df.drop(columns=["regime"]) if "regime" in df.columns else df

            trades, equity_curve = run_backtest(df_for_bt, cfg)
            metrics = compute_metrics(trades, equity_curve)

            combo_key = f"{key}_OR{or_minutes}"
            equity_by_combo[combo_key] = equity_curve

            row = {"dataset": label, "or_minutes": or_minutes, **metrics}
            rows.append(row)
            print(f"[OR={or_minutes:>2}min | {label}] {metrics['num_trades']} trades, "
                  f"return={metrics['total_return_pct']}%, sortino={metrics['sortino_ratio']}, "
                  f"profit_factor={metrics['profit_factor']}")

    # ---------------- Tabla comparativa ----------------
    cols = [
        "dataset", "or_minutes", "num_trades", "total_return_pct", "win_rate_pct",
        "profit_factor", "expectancy_R", "max_drawdown_pct", "sharpe_ratio", "sortino_ratio",
    ]
    md_path = outdir / "or_window_sweep_report.md"
    with open(md_path, "w") as f:
        f.write("# Barrido del rango de apertura (OR): 5/10/15/30/60 min\n\n")
        f.write(
            "Mismo motor (filtro de volumen + absorción CVD + SL/TP por swings), "
            "solo cambia cuántos minutos de la apertura de NY se usan para marcar "
            "el high/low inicial. Sobre los 3 datasets sintéticos A/B/C.\n\n"
        )
        f.write("| " + " | ".join(cols) + " |\n")
        f.write("|" + "---|" * len(cols) + "\n")
        for row in rows:
            f.write("| " + " | ".join(str(row.get(c, "")) for c in cols) + " |\n")
        f.write(
            "\n**Nota**: precios SINTÉTICOS — sirve para ver sensibilidad al "
            "parámetro `or_minutes`, no como estimación de rentabilidad real.\n"
        )

    with open(outdir / "or_window_sweep.json", "w") as f:
        json.dump(rows, f, indent=2, default=str)

    # ---------------- Gráfico: Sortino por dataset y ventana de OR ----------------
    fig, ax = plt.subplots(figsize=(10, 5))
    n_bars = len(OR_MINUTES_LIST)
    width = 0.8 / n_bars
    x = np.arange(len(DATASETS))
    for i, or_minutes in enumerate(OR_MINUTES_LIST):
        vals = [next(r["sortino_ratio"] for r in rows if r["or_minutes"] == or_minutes and r["dataset"] == label)
                for label, _ in DATASETS.values()]
        ax.bar(x + (i - (n_bars - 1) / 2) * width, vals, width, label=f"OR {or_minutes} min")
    ax.set_xticks(x)
    ax.set_xticklabels([label for label, _ in DATASETS.values()], fontsize=8)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Sortino ratio")
    ax.set_title("Sortino ratio por dataset y ventana de Opening Range")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(outdir / "sortino_by_or_window.png", dpi=140)
    plt.close(fig)

    # ---------------- Gráfico: equity curves por dataset (una línea por ventana de OR) ----------------
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=False)
    for ax, (key, (label, _)) in zip(axes, DATASETS.items()):
        for or_minutes in OR_MINUTES_LIST:
            ec = equity_by_combo[f"{key}_OR{or_minutes}"]
            ax.plot(ec.index, ec.values, label=f"OR {or_minutes} min")
        ax.set_title(label, fontsize=9)
        ax.legend(fontsize=7)
        ax.grid(alpha=0.3)
        ax.tick_params(axis="x", labelrotation=30, labelsize=7)
    fig.suptitle("Equity curve por ventana de OR, por dataset")
    fig.tight_layout()
    fig.savefig(outdir / "equity_curves_by_or_window.png", dpi=140)
    plt.close(fig)

    print(f"\nReporte guardado en {outdir}/: or_window_sweep_report.md, "
          f"or_window_sweep.json, sortino_by_or_window.png, equity_curves_by_or_window.png")


if __name__ == "__main__":
    main()
