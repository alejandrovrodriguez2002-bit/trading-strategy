#!/usr/bin/env python3
"""Corre el backtest completo y genera el reporte en results/.

Uso:
    # con datos sintéticos de demo (no son datos reales de mercado)
    python scripts/run_backtest.py --synthetic

    # con tus propios datos (CSV con columnas Date/Open/High/Low/Close/Volume)
    python scripts/run_backtest.py --csv data/QQQ_5m.csv
"""
import argparse
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
from src.synthetic import generate_synthetic_ohlcv  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/strategy_config.yaml")
    parser.add_argument("--csv", default=None, help="Ruta a CSV de velas OHLCV propio")
    parser.add_argument("--synthetic", action="store_true", help="Usar datos sintéticos de demo")
    parser.add_argument("--outdir", default="results")
    args = parser.parse_args()

    cfg = Config.from_yaml(args.config)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.csv:
        df = load_csv(args.csv, tz=cfg.timezone)
        data_label = f"CSV real: {args.csv}"
    elif args.synthetic:
        df = generate_synthetic_ohlcv(months_back=cfg.months_back, tz=cfg.timezone)
        data_label = "SINTÉTICO (demo, NO son datos reales de mercado)"
    else:
        parser.error("Debes pasar --csv <archivo> o --synthetic")
        return

    trades, equity_curve = run_backtest(df, cfg)
    metrics = compute_metrics(trades, equity_curve)

    trades_path = outdir / "trades.csv"
    trades.to_csv(trades_path, index=False)

    metrics_path = outdir / "metrics_summary.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    fig, ax = plt.subplots(figsize=(10, 5))
    equity_curve.plot(ax=ax)
    ax.set_title(f"Equity curve — {cfg.ticker} ({data_label})")
    ax.set_ylabel("Equity ($)")
    ax.set_xlabel("Fecha")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(outdir / "equity_curve.png", dpi=140)

    summary_md = outdir / "metrics_summary.md"
    with open(summary_md, "w") as f:
        f.write(f"# Resultados del backtest\n\nFuente de datos: {data_label}\n\n")
        f.write(f"Ticker: {cfg.ticker} | Intervalo: {cfg.interval} | ")
        f.write(f"Rango: {df.index.min()} -> {df.index.max()}\n\n")
        f.write("| Métrica | Valor |\n|---|---|\n")
        for k, v in metrics.items():
            f.write(f"| {k} | {v} |\n")

    print(f"Fuente de datos: {data_label}")
    print(json.dumps(metrics, indent=2, default=str))
    print(f"\nGuardado en {outdir}/: trades.csv, metrics_summary.json, metrics_summary.md, equity_curve.png")


if __name__ == "__main__":
    main()
