"""Cumulative Volume Delta (CVD) aproximado a partir de velas OHLCV.

No tenemos datos de tick / bid-ask, así que aproximamos el volumen
comprador vs. vendedor dentro de cada vela con la fórmula estándar
("Volume Delta" tipo TradingView/Bookmap cuando no hay datos de nivel 2):

    delta = volume * ((close - low) - (high - close)) / (high - low)

Intuición: si el cierre está cerca del high, la vela fue mayormente
agresión compradora (delta positivo); si cierra cerca del low, fue
mayormente agresión vendedora (delta negativo). Si high == low
(vela sin rango) no hay información direccional y delta = 0.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def add_bar_delta(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    rng = df["high"] - df["low"]
    with np.errstate(divide="ignore", invalid="ignore"):
        delta = df["volume"] * ((df["close"] - df["low"]) - (df["high"] - df["close"])) / rng
    delta = delta.where(rng > 0, 0.0)
    df["delta"] = delta
    return df


def add_cvd(df: pd.DataFrame, reset_daily: bool = True) -> pd.DataFrame:
    """Agrega columnas 'delta' y 'cvd' (delta acumulado).

    reset_daily=True reinicia el acumulado en cada apertura de sesión,
    lo cual es lo correcto para una estrategia intradía como esta (el
    CVD se compara solo dentro del mismo día de trading).
    """
    df = add_bar_delta(df)
    if reset_daily:
        day_key = df.index.tz_convert(df.index.tz).date
        df["cvd"] = df.groupby(day_key)["delta"].cumsum()
    else:
        df["cvd"] = df["delta"].cumsum()
    return df
