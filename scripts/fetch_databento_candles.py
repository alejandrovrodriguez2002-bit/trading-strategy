#!/usr/bin/env python3
"""
Extrae velas OHLCV de Databento para NASDAQ (o el instrumento/dataset que
elijas) y las exporta a CSV, en el mismo formato que
scripts/fetch_nasdaq_candles.py (Datetime,Open,High,Low,Close,Volume) para
que sean compatibles con src/data.py: load_csv sin cambios.

A diferencia de Yahoo Finance, Databento entrega HISTORIA REAL de meses o
años en 1 minuto (no solo ~7-60 días) — es justo lo que hace falta para
el backtest de 6 meses de esta estrategia. Es un servicio de PAGO: revisa
tu plan/cuota antes de pedir rangos largos (--days grande).

Requiere la librería oficial `databento` (pip install databento) y una
API key válida en la variable de entorno DATABENTO_API_KEY (nunca la
pases por línea de comandos ni la escribas en este archivo — en el
workflow de GitHub Actions viene de un "secret" del repo).

Se pide solo el schema "ohlcv-1m" (la base más barata/fina) y el resto de
timeframes (2/3/5/10/15/30/60 min) se derivan localmente por resample —
así no se paga por descargar el mismo rango varias veces en distintos
schemas.

⚠️ Este script se escribió sin poder probarlo de punta a punta contra la
API real de Databento (sin acceso de red a Databento desde ese entorno) —
se verificó la firma exacta del SDK oficial (db.Historical.timeseries.
get_range, DBNStore.to_df) instalando el paquete, pero no una llamada
real. Si algo no calza con la respuesta real de tu cuenta/plan (columnas,
dataset/schema disponibles, etc.), pásame el error exacto y se ajusta.

Datasets típicos para Nasdaq / Nasdaq-100 (ajusta --dataset según tu plan):
    XNAS.ITCH   -> Nasdaq TotalView-ITCH (equities listadas en Nasdaq, ej. QQQ, AAPL)
    DBEQ.BASIC  -> Databento Equities Basic (consolidado multi-exchange, si tu plan lo incluye)
    GLBX.MDP3   -> CME Globex (futuros, ej. NQ.c.0 para el E-mini Nasdaq-100 continuo)

Uso:
    export DATABENTO_API_KEY="tu-api-key"
    python3 scripts/fetch_databento_candles.py \
        --dataset XNAS.ITCH --symbols QQQ --days 180 --outdir data
"""
import argparse
import os
import sys
from pathlib import Path

import pandas as pd

DERIVED_TIMEFRAMES = {
    "2m": "2min", "3m": "3min", "5m": "5min",
    "10m": "10min", "15m": "15min", "30m": "30min", "60m": "60min",
}

REQUIRED_COLS = ["Open", "High", "Low", "Close", "Volume"]


def fetch_ohlcv_1m(dataset: str, symbols: list[str], start: str, end: str, stype_in: str, tz: str) -> pd.DataFrame:
    import databento as db

    api_key = os.environ.get("DATABENTO_API_KEY")
    if not api_key:
        sys.exit(
            "Falta la variable de entorno DATABENTO_API_KEY. "
            "Expórtala localmente o configúrala como 'secret' en el workflow de GitHub Actions."
        )

    client = db.Historical(key=api_key)
    store = client.timeseries.get_range(
        dataset=dataset,
        symbols=symbols,
        schema="ohlcv-1m",
        start=start,
        end=end,
        stype_in=stype_in,
    )
    return store.to_df(tz=tz)


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza la respuesta de Databento (to_df) al formato
    Datetime,Open,High,Low,Close,Volume que espera src/data.py: load_csv."""
    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(
            f"Se esperaba un DatetimeIndex (ts_event/ts_recv) en la respuesta de Databento. "
            f"Columnas disponibles: {list(df.columns)}"
        )
    df.index.name = "Datetime"

    rename = {c: c.capitalize() for c in ["open", "high", "low", "close", "volume"] if c in df.columns}
    df = df.rename(columns=rename)

    missing = set(REQUIRED_COLS) - set(df.columns)
    if missing:
        raise ValueError(
            f"Faltan columnas esperadas en la respuesta de Databento: {missing}. "
            f"Columnas disponibles: {list(df.columns)}"
        )
    keep = REQUIRED_COLS + (["symbol"] if "symbol" in df.columns else [])
    return df[keep].sort_index()


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    out = df.resample(rule).agg(agg).dropna(subset=["Open", "High", "Low", "Close"])
    return out


def restrict_to_regular_session(df: pd.DataFrame) -> pd.DataFrame:
    """Filtra a horario regular NY 09:30-16:00 (muchos datasets de Databento
    entregan 24h, incluyendo pre/post-market)."""
    return df.between_time("09:30", "16:00", inclusive="left")


def save_csv(df: pd.DataFrame, path: Path, timeframe: str):
    if df.empty:
        print(f"[AVISO] Sin datos para timeframe {timeframe}.")
        return
    out = df.reset_index()
    out.to_csv(path, index=False)
    print(f"[OK] {timeframe}: {len(out)} velas -> {path}")


def main():
    parser = argparse.ArgumentParser(description="Extrae velas OHLCV de Databento y exporta a CSV.")
    parser.add_argument("--dataset", default="XNAS.ITCH", help="Dataset de Databento (ver docstring)")
    parser.add_argument("--symbols", default="QQQ", help="Símbolo(s) separados por coma (ej. QQQ o NQ.c.0)")
    parser.add_argument("--stype-in", default="raw_symbol",
                         help="Tipo de símbolo de entrada: raw_symbol, parent, continuous, etc.")
    parser.add_argument("--days", type=int, default=180,
                         help="Días hacia atrás a solicitar (Databento sí soporta rangos largos; "
                              "ojo con tu cuota/costo)")
    parser.add_argument("--start", default=None, help="Fecha de inicio explícita (YYYY-MM-DD), sobreescribe --days")
    parser.add_argument("--end", default=None, help="Fecha de fin explícita (YYYY-MM-DD), por defecto hoy")
    parser.add_argument("--tz", default="America/New_York")
    parser.add_argument("--outdir", default="data", help="Directorio de salida para los CSV")
    parser.add_argument("--all-hours", action="store_true", help="No filtrar a horario regular 09:30-16:00 NY")
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    end = args.end or pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    start = args.start or (pd.Timestamp.utcnow() - pd.Timedelta(days=args.days)).strftime("%Y-%m-%d")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"Descargando ohlcv-1m de {args.dataset} para {symbols} ({start} -> {end})...")
    raw = fetch_ohlcv_1m(args.dataset, symbols, start, end, args.stype_in, args.tz)
    df_1m = normalize(raw)
    if not args.all_hours:
        df_1m = restrict_to_regular_session(df_1m)

    # si vinieron varios símbolos, se separa un CSV por símbolo
    groups = df_1m.groupby("symbol") if "symbol" in df_1m.columns and df_1m["symbol"].nunique() > 1 else [(symbols[0], df_1m)]

    for symbol, g in groups:
        symbol_slug = str(symbol).replace("^", "").replace("/", "_").replace(".", "_")
        g = g.drop(columns=["symbol"], errors="ignore")

        save_csv(g, outdir / f"databento_{symbol_slug}_1m_candles.csv", "1m")
        for tf, rule in DERIVED_TIMEFRAMES.items():
            g_tf = resample_ohlcv(g, rule)
            save_csv(g_tf, outdir / f"databento_{symbol_slug}_{tf}_candles.csv", tf)


if __name__ == "__main__":
    main()
