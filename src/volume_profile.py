"""Perfil de volumen semanal: Punto de Control (POC) y bandas de
desviación estándar.

POC = nivel de precio con más volumen operado en la semana — un "imán"
de precio / zona de rotación donde el mercado tiende a consolidar en vez
de tender con fuerza.

Además de el POC, se calcula la media y desviación estándar del precio
ponderadas por volumen (equivalente a un VWAP semanal ± bandas de
desviación estándar). El filtro de entrada usa estas bandas: solo se
acepta una entrada si su distancia a la media de la semana ANTERIOR
completa (nunca la semana en curso, que todavía no terminó — evita
look-ahead) cae entre 1 y 2 desviaciones estándar — ni tan pegada al
"centro de gravedad" del precio (bajo potencial de recorrido) ni tan
extendida (posible sobre-extensión / outlier).
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


def weekly_stats(df: pd.DataFrame, bin_pct: float = 0.0005) -> dict[WeekKey, dict]:
    """Por semana ISO, calculado SOLO con los datos de esa semana:
      - poc: nivel de precio con más volumen (bins de ancho `bin_pct` del
        precio medio de la semana)
      - mean: precio medio ponderado por volumen (~VWAP semanal)
      - std: desviación estándar del precio ponderada por volumen

    Precio típico por vela = (high+low+close)/3, ponderado por el volumen
    de la vela (aproximación estándar de volume profile a partir de OHLCV,
    sin datos de tick).
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    week_keys = np.array([_iso_week_key(ts) for ts in df.index])

    stats: dict[WeekKey, dict] = {}
    for key in {tuple(k) for k in map(tuple, week_keys)}:
        mask = np.all(week_keys == key, axis=1)
        sub_price = typical_price.values[mask]
        sub_vol = df["volume"].values[mask]
        if sub_vol.sum() <= 0:
            continue

        mean = float(np.average(sub_price, weights=sub_vol))
        variance = float(np.average((sub_price - mean) ** 2, weights=sub_vol))
        std = float(np.sqrt(variance))

        bin_size = sub_price.mean() * bin_pct
        poc = mean
        if bin_size > 0:
            bins = np.round(sub_price / bin_size) * bin_size
            vol_by_bin = pd.Series(sub_vol).groupby(bins).sum()
            poc = float(vol_by_bin.idxmax())

        stats[key] = {"poc": poc, "mean": mean, "std": std}
    return stats


def get_prior_week_stats(stats: dict[WeekKey, dict], timestamp: pd.Timestamp) -> dict | None:
    """Stats de la semana ISO anterior a la de `timestamp` (None si no hay
    semana previa con datos, p.ej. la primera semana del dataset)."""
    prior_key = _prior_week_key(_iso_week_key(timestamp))
    return stats.get(prior_key)


# --- compatibilidad: solo el POC, como antes ---

def weekly_poc(df: pd.DataFrame, bin_pct: float = 0.0005) -> dict[WeekKey, float]:
    return {key: s["poc"] for key, s in weekly_stats(df, bin_pct).items()}


def get_prior_week_poc(pocs: dict[WeekKey, float], timestamp: pd.Timestamp) -> float:
    prior_key = _prior_week_key(_iso_week_key(timestamp))
    return pocs.get(prior_key, float("nan"))
