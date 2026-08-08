#!/usr/bin/env python3
"""Descarga velas intradía con yfinance y las guarda en data/.

Uso:
    python scripts/download_data.py --ticker QQQ --interval 5m --months 6

NOTA: Yahoo Finance limita el historial intradía disponible (ver
docstring de src/data.py). Para 6 meses reales de velas de 1-5 min con
volumen fiable, usa un proveedor de datos (Databento, Polygon, IBKR,
export de TradingView, etc.) y carga el CSV resultante con
`--csv-passthrough` o directamente vía src.data.load_csv.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import fetch_yfinance  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="QQQ")
    parser.add_argument("--interval", default="5m")
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    df = fetch_yfinance(args.ticker, interval=args.interval, months_back=args.months)
    out_path = args.out or f"data/{args.ticker}_{args.interval}.csv"
    df.to_csv(out_path)
    print(f"Guardado {len(df)} velas en {out_path}")


if __name__ == "__main__":
    main()
