#!/usr/bin/env python3
"""Corre el backtest de la estrategia ORB+CVD sobre los 3 datasets sintéticos
(A: tradicional, B: SOC/multifractal, C: regime-switching híbrido) y genera
un reporte comparativo en results/comparison/.

Esto es una PRUEBA DE ROBUSTEZ (¿el "edge" de la estrategia depende de
supuestos de mercado Gaussiano/tradicional, o se sostiene bajo dinámicas de
colas pesadas / criticidad auto-organizada / regime-switching?), NO una
estimación de rentabilidad real — para eso hace falta el CSV de datos reales
(ver README.md).

Uso:
    python scripts/run_dataset_comparison.py
    python scripts/run_dataset_comparison.py --months 6 --config config/strategy_config.yaml
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from src.backtest import run_backtest  # noqa: E402
from src.config import Config  # noqa: E402
from src.metrics import compute_metrics  # noqa: E402
from src.synthetic_datasets import generate_dataset_a, generate_dataset_b, generate_dataset_c  # noqa: E402

DATASETS = {
    "A_tradicional": ("Dataset A — GBM + GARCH(1,1) (tradicional)", generate_dataset_a),
    "B_soc": ("Dataset B — Cascada multifractal + Hawkes power-law (SOC)", generate_dataset_b),
    "C_regime": ("Dataset C — Regime-switching (A↔B)", generate_dataset_c),
}


def _return_diagnostics(df) -> dict:
    ret = df["close"].pct_change().dropna()
    r2 = ret**2
    return {
        "ret_std": round(float(ret.std()), 5),
        "skew": round(float(stats.skew(ret)), 3),
        "excess_kurtosis": round(float(stats.kurtosis(ret)), 2),
        "acf_r2_lag1": round(float(r2.autocorr(1)), 3),
        "acf_r2_lag5": round(float(r2.autocorr(5)), 3),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/strategy_config.yaml")
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--outdir", default="results/comparison")
    args = parser.parse_args()

    cfg = Config.from_yaml(args.config)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rows = []
    equity_curves = {}
    return_series = {}

    for key, (label, gen) in DATASETS.items():
        df = gen(months_back=args.months)
        diag = _return_diagnostics(df)

        df_for_bt = df.drop(columns=["regime"]) if "regime" in df.columns else df
        trades, equity_curve = run_backtest(df_for_bt, cfg)
        metrics = compute_metrics(trades, equity_curve)

        ds_dir = outdir / key
        ds_dir.mkdir(parents=True, exist_ok=True)
        trades.to_csv(ds_dir / "trades.csv", index=False)
        with open(ds_dir / "metrics.json", "w") as f:
            json.dump({**diag, **metrics}, f, indent=2, default=str)

        equity_curves[key] = equity_curve
        return_series[key] = df["close"].pct_change().dropna()

        rows.append({"dataset": label, **diag, **metrics})
        print(f"[{key}] {label}: {metrics['num_trades']} trades, "
              f"return={metrics['total_return_pct']}%, sortino={metrics['sortino_ratio']}, "
              f"kurtosis={diag['excess_kurtosis']}")

    # ---------------- Tabla comparativa (Markdown) ----------------
    cols = [
        "dataset", "ret_std", "excess_kurtosis", "acf_r2_lag1", "num_trades",
        "total_return_pct", "win_rate_pct", "profit_factor", "expectancy_R",
        "max_drawdown_pct", "sharpe_ratio", "sortino_ratio",
    ]
    md_path = outdir / "comparison_report.md"
    with open(md_path, "w") as f:
        f.write("# Comparación de robustez: ORB + Absorción CVD sobre 3 mercados sintéticos\n\n")
        f.write(
            "Los tres datasets tienen volatilidad total comparable (mismo orden de "
            "magnitud de `ret_std`); lo que cambia es la FORMA de la distribución y "
            "la dinámica temporal (colas, clustering), para aislar si el resultado "
            "de la estrategia depende de supuestos de mercado 'tradicionales'.\n\n"
        )
        f.write("| " + " | ".join(cols) + " |\n")
        f.write("|" + "---|" * len(cols) + "\n")
        for row in rows:
            f.write("| " + " | ".join(str(row.get(c, "")) for c in cols) + " |\n")
        f.write(
            "\n**Nota**: estos resultados son sobre precios SINTÉTICOS — sirven para "
            "ver si la estrategia es frágil ante colas pesadas / criticidad "
            "auto-organizada, no como estimación de rentabilidad real.\n"
        )

    # ---------------- Gráfico: equity curves superpuestas ----------------
    fig, ax = plt.subplots(figsize=(10, 5))
    for key, ec in equity_curves.items():
        ax.plot(ec.index, ec.values, label=DATASETS[key][0])
    ax.set_title("Equity curve por dataset sintético")
    ax.set_ylabel("Equity ($)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(outdir / "comparison_equity_curves.png", dpi=140)
    plt.close(fig)

    # ---------------- Gráfico: distribución de retornos (log-y, colas) ----------------
    fig, ax = plt.subplots(figsize=(10, 5))
    for key, r in return_series.items():
        ax.hist(r, bins=200, alpha=0.5, density=True, label=DATASETS[key][0], histtype="step", linewidth=1.5)
    ax.set_yscale("log")
    ax.set_title("Distribución de retornos por vela (escala log en Y — muestra las colas)")
    ax.set_xlabel("Retorno por vela")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(outdir / "comparison_return_distributions.png", dpi=140)
    plt.close(fig)

    print(f"\nReporte guardado en {outdir}/: comparison_report.md, "
          f"comparison_equity_curves.png, comparison_return_distributions.png, "
          f"y trades.csv/metrics.json por dataset.")


if __name__ == "__main__":
    main()
