#!/usr/bin/env python3
"""
Extrae velas (OHLCV) del Nasdaq Composite (^IXIC) en timeframes de 1 a 5
minutos desde Yahoo Finance y las exporta a CSV.

Limitaciones de Yahoo Finance para datos intradía:
  - Velas de 1 minuto: solo se pueden pedir hasta ~7 días hacia atrás, y
    cada request individual no puede abarcar más de 7 días.
  - Velas de 2m/5m (y 15m/30m/60m/90m): disponibles hasta ~60 días atrás.

Por eso, si se pide un rango de 30 días, el timeframe de 1 minuto se
recorta automáticamente a los últimos ~7 días (lo máximo que ofrece la
fuente gratuita), y el resto de timeframes (2m, 3m*, 5m) usan el rango
completo solicitado.

  * Yahoo Finance no ofrece nativamente velas de 3 minutos, así que se
    generan agregando (resample) las velas de 1 minuto.

Uso:
    python3 fetch_nasdaq_candles.py --symbol ^IXIC --days 30 --outdir ../data
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

# Timeframes soportados y su límite de historia intradía en Yahoo Finance.
TIMEFRAMES = {
    "1m": {"interval": "1m", "max_days": 7},
    "2m": {"interval": "2m", "max_days": 60},
    "3m": {"interval": None, "max_days": 60, "resample_from": "1m", "rule": "3min"},
    "5m": {"interval": "5m", "max_days": 60},
}


def fetch_interval(symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
    df = yf.download(
        tickers=symbol,
        interval=interval,
        start=start,
        end=end,
        progress=False,
        auto_adjust=False,
        prepost=False,
    )
    if df.empty:
        return df
    # yfinance puede devolver columnas MultiIndex cuando se pasa un solo ticker
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index.name = "Datetime"
    return df


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    agg = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Adj Close": "last",
        "Volume": "sum",
    }
    agg = {k: v for k, v in agg.items() if k in df.columns}
    out = df.resample(rule).agg(agg).dropna(subset=["Open", "High", "Low", "Close"])
    return out


def save_csv(df: pd.DataFrame, path: Path, symbol: str, timeframe: str):
    if df.empty:
        print(f"[AVISO] Sin datos para {symbol} en timeframe {timeframe}.")
        return
    out = df.reset_index()
    # Normaliza el nombre de la columna de tiempo (puede venir como 'Datetime' o 'index')
    time_col = out.columns[0]
    out = out.rename(columns={time_col: "Datetime"})
    keep = [c for c in ["Datetime", "Open", "High", "Low", "Close", "Adj Close", "Volume"] if c in out.columns]
    out = out[keep]
    out.to_csv(path, index=False)
    print(f"[OK] {timeframe}: {len(out)} velas -> {path}")


def main():
    parser = argparse.ArgumentParser(description="Extrae velas OHLCV del Nasdaq y exporta a CSV.")
    parser.add_argument("--symbol", default="^IXIC", help="Símbolo (por defecto ^IXIC = Nasdaq Composite)")
    parser.add_argument("--days", type=int, default=30, help="Días hacia atrás a solicitar (por defecto 30)")
    parser.add_argument("--outdir", default="data", help="Directorio de salida para los CSV")
    args = parser.parse_args()

    end = datetime.now(timezone.utc)
    requested_start = end - timedelta(days=args.days)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    symbol_slug = args.symbol.replace("^", "").replace("/", "_")

    cache_1m = None  # para poder derivar 3m sin volver a descargar

    for tf, cfg in TIMEFRAMES.items():
        max_days = cfg["max_days"]
        effective_days = min(args.days, max_days)
        start = end - timedelta(days=effective_days)

        if cfg.get("resample_from"):
            base_tf = cfg["resample_from"]
            if cache_1m is None:
                base_start = end - timedelta(days=min(args.days, TIMEFRAMES[base_tf]["max_days"]))
                cache_1m = fetch_interval(args.symbol, TIMEFRAMES[base_tf]["interval"], base_start, end)
            df = resample_ohlcv(cache_1m, cfg["rule"]) if not cache_1m.empty else cache_1m
        else:
            df = fetch_interval(args.symbol, cfg["interval"], start, end)
            if tf == "1m":
                cache_1m = df

        if effective_days < args.days:
            print(f"[INFO] Timeframe {tf}: recortado a los últimos {effective_days} días "
                  f"(límite de Yahoo Finance para este intervalo).")

        filename = f"nasdaq_{symbol_slug}_{tf}_candles.csv"
        save_csv(df, outdir / filename, args.symbol, tf)


if __name__ == "__main__":
    sys.exit(main())
