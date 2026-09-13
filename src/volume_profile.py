"""Perfil de volumen semanal y Punto de Control (POC).

POC = nivel de precio con más volumen operado en la semana — un "imán"
de precio / zona de rotación donde el mercado tiende a consolidar en vez
de tender con fuerza. Se usa para filtrar entradas: si el precio de
entrada de un trade queda demasiado cerca del POC de la semana ANTERIOR
completa (nunca la semana en curso, que todavía no terminó — evita
look-ahead), se descarta esa entrada.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

WeekKey = tuple[int, int]  # (año ISO, semana ISO)


def _iso_week_key(ts: pd.Timestamp) -> WeekKey:
    y, w, _ = ts.isocalendar()
    return (int(y), int(w))


def _prior_week_key(key: WeekKey) -> WeekKey:
    year, week = key
    monday = dt.date.fromisocalendar(year, week, 1)
    prior_monday = monday - dt.timedelta(weeks=1)
    y2, w2, _ = prior_monday.isocalendar()
    return (int(y2), int(w2))


def weekly_poc(df: pd.DataFrame, bin_pct: float = 0.0005) -> dict[WeekKey, float]:
    """POC por semana ISO, calculado SOLO con los datos de esa semana.

    Aproximación estándar de volume profile a partir de velas OHLCV (sin
    datos de tick): precio típico = (high+low+close)/3, ponderado por el
    volumen de la vela, agrupado en bins de ancho `bin_pct` del precio
    medio de la semana. El POC es el bin con más volumen acumulado.
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    week_keys = np.array([_iso_week_key(ts) for ts in df.index])

    pocs: dict[WeekKey, float] = {}
    for key in {tuple(k) for k in map(tuple, week_keys)}:
        mask = np.all(week_keys == key, axis=1)
        sub_price = typical_price.values[mask]
        sub_vol = df["volume"].values[mask]
        if sub_vol.sum() <= 0:
            continue
        bin_size = sub_price.mean() * bin_pct
        if bin_size <= 0:
            continue
        bins = np.round(sub_price / bin_size) * bin_size
        vol_by_bin = pd.Series(sub_vol).groupby(bins).sum()
        pocs[key] = float(vol_by_bin.idxmax())
    return pocs


def get_prior_week_poc(pocs: dict[WeekKey, float], timestamp: pd.Timestamp) -> float:
    """POC de la semana ISO anterior a la de `timestamp` (nan si no hay
    semana previa con datos, p.ej. la primera semana del dataset)."""
    prior_key = _prior_week_key(_iso_week_key(timestamp))
    return pocs.get(prior_key, float("nan"))
