"""Carga y normalización de datos OHLCV (CSV local o descarga con yfinance)."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

REQUIRED_COLS = ["open", "high", "low", "close", "volume"]

_COLUMN_ALIASES = {
    "date": "datetime", "time": "datetime", "timestamp": "datetime", "datetime": "datetime",
    "open": "open", "o": "open",
    "high": "high", "h": "high",
    "low": "low", "l": "low",
    "close": "close", "c": "close", "adj close": "close", "adj_close": "close",
    "volume": "volume", "vol": "volume", "v": "volume",
}


def _fix_yahoo_zero_open_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Corrige un artefacto conocido de Yahoo Finance en datos intradía:
    la primera vela de cada sesión suele reportar volume=0 (el print de
    apertura no se agrega bien), justo la vela que más importa para una
    estrategia basada en la apertura de NY. Se reemplaza por el volumen de
    la vela siguiente del mismo día (aproximación razonable: la explosión
    de volumen de apertura casi siempre se sostiene 1-2 velas)."""
    if df.empty:
        return df
    dates = df.index.date
    is_new_day = np.concatenate(([True], dates[1:] != dates[:-1]))
    zero_open = is_new_day & (df["volume"] == 0)
    if zero_open.any():
        next_vol = df["volume"].shift(-1)
        df.loc[zero_open, "volume"] = next_vol[zero_open]
    return df


def load_csv(path: str | Path, tz: str = "America/New_York") -> pd.DataFrame:
    """Carga un CSV genérico de velas OHLCV y lo normaliza.

    Acepta encabezados comunes de TradingView / brokers / Databento
    (Date, Datetime, Open, High, Low, Close, Volume, en cualquier
    combinación de mayúsculas/minúsculas).
    """
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    rename = {c: _COLUMN_ALIASES[c] for c in df.columns if c in _COLUMN_ALIASES}
    df = df.rename(columns=rename)
    # CSVs de Yahoo suelen traer "Close" y "Adj Close" a la vez, y ambas
    # se mapean a "close" -> se queda con la primera y descarta el duplicado
    # (para un índice como ^IXIC son idénticas; no hay dividendos que ajustar)
    df = df.loc[:, ~df.columns.duplicated()]

    if "datetime" not in df.columns:
        raise ValueError(
            "El CSV debe tener una columna de fecha/hora (Date, Datetime o Timestamp)."
        )
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas en el CSV: {missing}")

    df["datetime"] = pd.to_datetime(df["datetime"], utc=False)
    df = df.set_index("datetime").sort_index()

    if df.index.tz is None:
        df.index = df.index.tz_localize(tz)
    else:
        df.index = df.index.tz_convert(tz)

    df = df[REQUIRED_COLS].astype(float)
    df["volume"] = df["volume"].fillna(0)
    df = df.dropna(subset=["open", "high", "low", "close"])
    return _fix_yahoo_zero_open_volume(df)


def fetch_yfinance(
    ticker: str,
    interval: str = "5m",
    months_back: int = 6,
    tz: str = "America/New_York",
) -> pd.DataFrame:
    """Descarga velas intradía con yfinance.

    NOTA IMPORTANTE (limitación de Yahoo Finance, no de este código):
    Yahoo solo entrega historial intradía reciente:
      - 1m  -> últimos ~7-8 días
      - 2m/5m/15m/30m/90m -> últimos ~60 días
      - 60m/1h -> últimos ~730 días (pero es demasiado tosco para un
        rango de apertura de 15 min y para CVD)
    Para pedir 6 meses reales de velas de 1-5 min necesitas un proveedor
    de pago (Databento, Polygon, IBKR, TradingView export, etc.) y luego
    cargar ese archivo con `load_csv`. Esta función hace *best effort* y
    yfinance recortará silenciosamente el rango si excede el límite.
    """
    import yfinance as yf

    end = datetime.now(ZoneInfo(tz))
    start = end - timedelta(days=months_back * 30)

    df = yf.download(
        ticker,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        interval=interval,
        progress=False,
        auto_adjust=False,
    )
    if df.empty:
        raise RuntimeError(
            f"yfinance no devolvió datos para {ticker} ({interval}, {months_back}m). "
            "Es probable que hayas excedido el límite de historial intradía de Yahoo, "
            "o que no haya acceso de red saliente desde este entorno."
        )

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0].lower() for c in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]

    df = df.rename(columns={"adj close": "close"})
    df = df[REQUIRED_COLS]

    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert(tz)
    return df.sort_index()


def restrict_to_session(
    df: pd.DataFrame, session_open: str, session_close: str
) -> pd.DataFrame:
    """Filtra las velas al horario regular de sesión (por hora local, cada día)."""
    return df.between_time(session_open, session_close, inclusive="left")
