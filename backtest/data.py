"""
Carga, limpieza y validación de las velas de 1 minuto del futuro E-mini
Nasdaq-100 (NQ, CME Globex, Databento GLBX.MDP3, símbolo continuo NQ.c.0).

El CSV crudo vive en la rama `data-exports` (data/databento_NQ_c_0_1m_candles.csv),
generado por scripts/fetch_databento_candles.py con --all-hours. No trae la
columna de contrato, así que aquí se reconstruye:

  * Rolls: NQ.c.0 es "calendar roll": sigue al contrato front hasta su
    vencimiento (3er viernes de Mar/Jun/Sep/Dic, 09:30 ET, o el día hábil
    anterior si es feriado) y salta al siguiente en la primera vela posterior.
    Un cierre de un contrato NO es comparable con la apertura del siguiente
    (base/carry de ~0.5-1 %), así que cualquier retorno que cruce un roll se
    invalida en lugar de inventar un ajuste.
  * Calendario de contado: ambas estrategias son de la sesión regular de
    Nueva York (09:30-16:00). Se usan las reglas de feriados de NYSE, lo que
    descarta los días en los que el futuro sí cotiza con sesión recortada
    (Memorial Day, Juneteenth, 3 de julio, Labor Day...). Ojo: el CSV del VIX
    trae filas en esos feriados (sesión extendida de CBOE), por eso NO se usa
    como calendario.
  * Liquidez: en la semana de vencimiento el contrato front casi no opera
    (todo el mercado ya rodó al siguiente). Esos días el precio de NQ.c.0
    viene de un libro delgado y no es ejecutable a tamaño, así que se marcan
    como no operables (volumen RTH < 35 % de la mediana).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

TZ = "America/New_York"
RTH_MINUTES = 390  # 09:30 .. 15:59 (velas etiquetadas por su apertura)
LIQUIDITY_MIN_FRACTION = 0.35
MAX_MISSING_MINUTES = 5


def load_raw(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True).dt.tz_convert(TZ)
    return df.set_index("Datetime").sort_index()


def load_vix(path: str | Path) -> pd.Series:
    v = pd.read_csv(path, parse_dates=["DATE"]).set_index("DATE")["CLOSE"]
    v.index = v.index.date
    return v.astype(float)


def _observed(d: pd.Timestamp) -> pd.Timestamp:
    if d.weekday() == 5:
        return d - pd.Timedelta(days=1)
    if d.weekday() == 6:
        return d + pd.Timedelta(days=1)
    return d


def _nth_weekday(year, month, weekday, n):
    first = pd.Timestamp(year=year, month=month, day=1)
    return first + pd.Timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def _last_weekday(year, month, weekday):
    last = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)
    return last - pd.Timedelta(days=(last.weekday() - weekday) % 7)


def _easter(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return pd.Timestamp(year=y, month=month, day=day)


def nyse_holidays(year: int) -> set:
    h = [_observed(pd.Timestamp(year=year, month=1, day=1)), _nth_weekday(year, 1, 0, 3), _nth_weekday(year, 2, 0, 3),
         _easter(year) - pd.Timedelta(days=2), _last_weekday(year, 5, 0),
         _observed(pd.Timestamp(year=year, month=6, day=19)), _observed(pd.Timestamp(year=year, month=7, day=4)),
         _nth_weekday(year, 9, 0, 1), _nth_weekday(year, 11, 3, 4), _observed(pd.Timestamp(year=year, month=12, day=25))]
    return {d.date() for d in h}


def nyse_trading_days(start, end) -> set:
    hol = set().union(*(nyse_holidays(y) for y in range(start.year, end.year + 1)))
    return {d.date() for d in pd.bdate_range(start.date(), end.date()) if d.date() not in hol}


def quarterly_expiries(start: pd.Timestamp, end: pd.Timestamp, cash_days: set) -> list[pd.Timestamp]:
    """Vencimientos de NQ: 3er viernes de Mar/Jun/Sep/Dic 09:30 ET (día hábil previo si es feriado)."""
    out = []
    for year in range(start.year, end.year + 1):
        for month in (3, 6, 9, 12):
            first = pd.Timestamp(year=year, month=month, day=1)
            d = first + pd.Timedelta(days=(4 - first.weekday()) % 7 + 14)  # 3er viernes
            while d.date() not in cash_days:
                d -= pd.Timedelta(days=1)
            out.append(pd.Timestamp(d.date()).tz_localize(TZ) + pd.Timedelta(hours=9, minutes=30))
    return [e for e in out if start <= e <= end]


@dataclass
class CleanData:
    bars: dict          # date -> DataFrame de 390 velas RTH (Open, High, Low, Close, Volume, VWAP)
    daily: pd.DataFrame  # una fila por día con banderas de calidad
    log: list           # bitácora de chequeos para el reporte


def build(raw: pd.DataFrame, vix: pd.Series) -> CleanData:
    log = []
    log.append(f"Velas crudas: {len(raw):,} ({raw.index.min()} -> {raw.index.max()})")

    # --- chequeos de integridad de cada vela -----------------------------
    dups = int(raw.index.duplicated().sum())
    raw = raw[~raw.index.duplicated(keep="first")]
    px = raw[["Open", "High", "Low", "Close"]]
    bad = (raw.High < px.max(axis=1)) | (raw.Low > px.min(axis=1)) | (px <= 0).any(axis=1) | px.isna().any(axis=1)
    log.append(f"Timestamps duplicados eliminados: {dups}")
    log.append(f"Velas con OHLC inconsistente / no positivo / NaN eliminadas: {int(bad.sum())}")
    raw = raw[~bad]

    # --- contratos (rolls) ---------------------------------------------
    cash_days = nyse_trading_days(raw.index.min() - pd.Timedelta(days=10), raw.index.max())
    expiries = quarterly_expiries(raw.index.min(), raw.index.max(),
                                  nyse_trading_days(raw.index.min(), raw.index.max() + pd.Timedelta(days=120)))
    contract = np.zeros(len(raw), dtype=int)
    for e in expiries:
        contract += (raw.index >= e).astype(int)
    raw = raw.assign(contract=contract)
    for e in expiries:
        before = raw[raw.index < e].tail(1)
        after = raw[raw.index >= e].head(1)
        if len(before) and len(after):
            gap = after.Open.iloc[0] / before.Close.iloc[0] - 1
            log.append(f"Roll detectado en vencimiento {e:%Y-%m-%d}: último precio contrato viejo "
                       f"{before.Close.iloc[0]:.2f} ({before.index[0]:%m-%d %H:%M}) -> primero del nuevo "
                       f"{after.Open.iloc[0]:.2f} ({after.index[0]:%m-%d %H:%M}), salto {gap:+.2%} (incluye base, no se usa)")

    # --- sesión regular ------------------------------------------------
    rth = raw.between_time("09:30", "15:59")
    grid = pd.timedelta_range("09:30:00", periods=RTH_MINUTES, freq="1min")
    bars, rows = {}, []
    for day, g in rth.groupby(rth.index.date):
        idx = pd.DatetimeIndex([pd.Timestamp(day).tz_localize(TZ) + t for t in grid])
        n_obs = len(g)
        g = g.reindex(idx)
        missing = int(g.Close.isna().sum())
        # minutos sin operaciones: precio plano en el último cierre, volumen 0
        g["Close"] = g.Close.ffill()
        for c in ("Open", "High", "Low"):
            g[c] = g[c].fillna(g.Close)
        g["Volume"] = g.Volume.fillna(0)
        g["contract"] = g.contract.ffill().bfill()
        tp = (g.High + g.Low + g.Close) / 3
        g["VWAP"] = (tp * g.Volume).cumsum() / g.Volume.cumsum().replace(0, np.nan)
        g["VWAP"] = g.VWAP.fillna(g.Close)
        bars[day] = g
        rows.append(dict(date=day, n_bars=n_obs, missing=missing, open=g.Open.iloc[0], close=g.Close.iloc[-1],
                         rth_volume=float(g.Volume.sum()), contract=int(g.contract.iloc[-1]),
                         first_bar_missing=bool(idx[0] not in rth.index)))
    daily = pd.DataFrame(rows).set_index("date")

    daily["cash_day"] = [d in cash_days for d in daily.index]
    med = daily.loc[daily.cash_day, "rth_volume"].median()
    daily["liquid"] = daily.rth_volume >= LIQUIDITY_MIN_FRACTION * med
    daily["complete"] = (daily.missing <= MAX_MISSING_MINUTES) & ~daily.first_bar_missing
    daily["tradable"] = daily.cash_day & daily.liquid & daily.complete

    # cierre previo = cierre RTH del día de contado anterior, solo si es el mismo contrato
    trad = daily[daily.cash_day]
    prev_close = trad.close.shift(1)
    same = trad.contract.eq(trad.contract.shift(1))
    daily["prev_close"] = prev_close.where(same)
    daily["prev_close_valid"] = daily.prev_close.notna()
    daily["ret_cc"] = daily.close / daily.prev_close - 1  # benchmark buy & hold (NaN si cruza roll)

    # VIX del día de contado anterior (se conoce antes de la apertura: sin look-ahead)
    vix_prev = vix[[d in cash_days for d in vix.index]].shift(1)
    daily["vix_prev_close"] = [vix_prev.get(d, np.nan) for d in daily.index]

    for d, r in daily[~daily.cash_day].iterrows():
        log.append(f"{d}: día NO hábil de contado (feriado NYSE, futuro con sesión recortada, {r.n_bars} velas RTH) -> excluido")
    for d, r in daily[daily.cash_day & ~daily.liquid & daily.complete].iterrows():
        log.append(f"{d}: contrato en semana de vencimiento, volumen RTH {r.rth_volume:,.0f} "
                   f"({r.rth_volume / med:.0%} de la mediana) -> no operable")
    for d, r in daily[daily.cash_day & ~daily.complete].iterrows():
        log.append(f"{d}: {r.missing} minutos RTH faltantes -> no operable")
    for d in daily[daily.cash_day & ~daily.prev_close_valid].index:
        log.append(f"{d}: cierre previo pertenece a otro contrato (o no existe) -> retornos close-to-close y "
                   f"gaps de ese día se invalidan")
    missing_cash = sorted(d for d in cash_days if daily.index.min() <= d <= daily.index.max() and d not in daily.index)
    for d in missing_cash:
        log.append(f"{d}: día hábil sin sesión RTH en NQ.c.0 (vencimiento del contrato a las 09:30) -> sin datos")
    log.append(f"Días con sesión RTH: {len(daily)}; hábiles de contado: {int(daily.cash_day.sum())}; "
               f"operables: {int(daily.tradable.sum())}; minutos faltantes rellenados en días operables (máx/día): "
               f"{int(daily.loc[daily.tradable, 'missing'].max())}")
    return CleanData(bars=bars, daily=daily, log=log)
