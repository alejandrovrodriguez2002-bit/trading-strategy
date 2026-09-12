"""Generador de datos SINTÉTICOS (demo) de velas OHLCV intradía.

Esto NO son datos reales de mercado. Sirven únicamente para validar que
el pipeline completo (datos -> CVD -> estrategia -> métricas) funciona
de punta a punta, ya que este entorno no tiene acceso de red a
proveedores de datos (ver README.md). Sustituye por datos reales antes
de sacar conclusiones sobre la estrategia.
"""
from __future__ import annotations

from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .synthetic_datasets import _open_volume_profile


def generate_synthetic_ohlcv(
    months_back: int = 6,
    interval_minutes: int = 5,
    start_price: float = 480.0,
    tz: str = "America/New_York",
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    end_date = pd.Timestamp.now(tz=ZoneInfo(tz)).normalize()
    start_date = end_date - pd.DateOffset(months=months_back)

    trading_days = pd.bdate_range(start_date, end_date)  # aproximación: días hábiles (sin festivos US)

    bars_per_day = int(390 / interval_minutes)  # sesión 9:30-16:00 = 390 min
    vol_profile_by_bar = _open_volume_profile(bars_per_day, bars_per_day)  # pico de volumen en la apertura
    rows = []
    price = start_price
    daily_vol_regime = rng.uniform(0.0006, 0.0016, size=len(trading_days))

    for day, sigma in zip(trading_days, daily_vol_regime):
        day_open_time = day + pd.Timedelta(hours=9, minutes=30)
        # pequeño gap overnight
        price *= 1 + rng.normal(0, 0.002)

        # régimen de tendencia intradía aleatorio para generar rupturas y pullbacks
        drift = rng.choice([-1, 0, 1], p=[0.35, 0.3, 0.35]) * rng.uniform(0.00003, 0.00012)

        for b in range(bars_per_day):
            ts = day_open_time + pd.Timedelta(minutes=interval_minutes * b)
            ret = rng.normal(drift, sigma)
            o = price
            c = o * (1 + ret)
            hi = max(o, c) * (1 + abs(rng.normal(0, sigma * 0.6)))
            lo = min(o, c) * (1 - abs(rng.normal(0, sigma * 0.6)))
            vol = max(1, rng.lognormal(mean=9.0, sigma=0.5) * vol_profile_by_bar[b])
            rows.append((ts, o, hi, lo, c, vol))
            price = c

    df = pd.DataFrame(rows, columns=["datetime", "open", "high", "low", "close", "volume"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize(ZoneInfo(tz))
    else:
        df.index = df.index.tz_convert(ZoneInfo(tz))
    return df
