"""
Generalización de la estrategia validada (fade del rango de apertura de
30 min de NY, ver `src/simple_orb.py` y el README) a OTRAS ventanas
horarias de 30 minutos: los primeros y los últimos 30 minutos de las
sesiones de Asia, Londres y Nueva York -- 6 "zonas" en total.

Requiere un instrumento que cotice ~24h (futuros, ej. NQ vía Databento
GLBX.MDP3) -- un ETF de acciones como QQQ no tiene velas en las sesiones
de Asia/Londres. Ver README.md para cómo se obtuvieron esos datos.

Misma lógica que la variante validada, sin reinventar nada:

1. Se marca el high/low de la ventana de 30 minutos de la zona.
2. Se busca, dentro de un horizonte de búsqueda (`search_hours` después
   del fin de la zona), el primer rompimiento de ese high/low.
3. Modo "fade" (default, el validado): se entra EN CONTRA del rompimiento
   -- rompe el high -> SHORT; rompe el low -> LONG. Relleno al nivel (o al
   open de la vela si abre en gap más allá).
4. Stop loss: el extremo real (mecha) de la vela que rompió el rango +
   buffer (0.03% por defecto) -- no el nivel de la zona.
5. Take profit: múltiplo fijo de R (1.5R por defecto, el mismo de la
   variante validada).
6. Si no toca ni SL ni TP dentro del horizonte de búsqueda, se cierra al
   precio de la última vela de ese horizonte.

Las sesiones (horario de NY, con el reloj típico de FX/futuros) y las 6
zonas resultantes se definen en `ZONES` al final de este archivo.
"""
from __future__ import annotations

import dataclasses
from typing import Optional

import pandas as pd

from .simple_orb import _find_breakout_fill
from .strategy import _apply_slippage, _simulate_exit


@dataclasses.dataclass
class SessionZoneConfig:
    zone_start: str  # "HH:MM", hora de NY
    zone_end: str  # "HH:MM", hora de NY (si <= zone_start, se asume que cruza medianoche)
    search_hours: float  # horas después de zone_end en las que se busca el rompimiento

    direction_mode: str = "fade"  # "fade" (validado) | "breakout" (continuación, referencia)
    tp_r_multiple: float = 1.5
    sl_buffer_pct: float = 0.03

    starting_equity: float = 10_000.0
    risk_per_trade_pct: float = 1.0
    max_leverage: Optional[float] = None
    slippage_bps: float = 1.0
    commission_per_trade: float = 0.0


@dataclasses.dataclass
class Trade:
    date: object  # fecha de referencia (día en que empieza la zona)
    direction: str
    zone_high: float
    zone_low: float
    entry_time: pd.Timestamp
    entry_price: float
    sl: float
    tp: float
    exit_time: pd.Timestamp
    exit_price: float
    exit_reason: str
    shares: float
    pnl: float
    r_multiple: float


def _hm_to_timedelta(hm: str) -> pd.Timedelta:
    h, m = (int(x) for x in hm.split(":"))
    return pd.Timedelta(hours=h, minutes=m)


def _iter_zone_occurrences(df: pd.DataFrame, cfg: SessionZoneConfig):
    """Genera, por cada fecha de referencia presente en el histórico,
    (ref_date, mark_start_pos, mark_end_pos, search_end_pos) para una
    ocurrencia de la zona -- se salta silenciosamente cualquier fecha sin
    datos en la ventana (fin de semana, feriado, hueco de mantenimiento)."""
    start_delta = _hm_to_timedelta(cfg.zone_start)
    end_delta = _hm_to_timedelta(cfg.zone_end)
    if end_delta <= start_delta:
        end_delta += pd.Timedelta(days=1)  # la zona cruza medianoche (ej. Asia 19:00-04:00)
    search_delta = end_delta + pd.Timedelta(hours=cfg.search_hours)

    tz = df.index.tz
    n = len(df)
    for ref_date in sorted(set(df.index.date)):
        ref_midnight = pd.Timestamp(ref_date, tz=tz)
        mark_start_ts = ref_midnight + start_delta
        mark_end_ts = ref_midnight + end_delta
        search_end_ts = ref_midnight + search_delta

        mark_start_pos = df.index.searchsorted(mark_start_ts)
        mark_end_pos = df.index.searchsorted(mark_end_ts)
        if mark_start_pos >= n or mark_end_pos <= mark_start_pos:
            continue  # sin datos en la ventana de marcado (fin de semana/feriado)

        search_end_pos = min(df.index.searchsorted(search_end_ts), n) - 1
        if search_end_pos <= mark_end_pos:
            continue

        yield ref_date, mark_start_pos, mark_end_pos, search_end_pos


def generate_trades_zone(df: pd.DataFrame, cfg: SessionZoneConfig) -> pd.DataFrame:
    """df debe incluir columnas open/high/low/close/volume, indexado en la
    tz de NY, SIN restringir a horario de sesión (se necesitan las 24h)."""
    trades: list[Trade] = []
    equity = cfg.starting_equity

    for ref_date, mark_start_pos, mark_end_pos, search_end_pos in _iter_zone_occurrences(df, cfg):
        mark_slice = df.iloc[mark_start_pos:mark_end_pos]
        if mark_slice.empty:
            continue
        zone_high = float(mark_slice["high"].max())
        zone_low = float(mark_slice["low"].min())
        if zone_high <= zone_low:
            continue

        breakout = _find_breakout_fill(df, mark_end_pos, search_end_pos, zone_high, zone_low)
        if breakout is None:
            continue
        breakout_pos, raw_direction, raw_fill_price, bar_high, bar_low = breakout

        if cfg.direction_mode == "fade":
            direction = "short" if raw_direction == "long" else "long"
            sl_anchor = bar_high if direction == "short" else bar_low
        else:
            direction = raw_direction
            sl_anchor = zone_low if direction == "long" else zone_high

        entry_pos = breakout_pos
        entry_price = _apply_slippage(raw_fill_price, direction, "entry", cfg.slippage_bps)

        buffer = entry_price * cfg.sl_buffer_pct / 100.0
        sl = (sl_anchor - buffer) if direction == "long" else (sl_anchor + buffer)
        risk = abs(entry_price - sl)
        if risk <= 0:
            continue
        tp = entry_price + cfg.tp_r_multiple * risk if direction == "long" else entry_price - cfg.tp_r_multiple * risk

        exit_pos, raw_exit_price, exit_reason = _simulate_exit(df, entry_pos, search_end_pos, direction, sl, tp)
        exit_price = _apply_slippage(raw_exit_price, direction, "exit", cfg.slippage_bps)

        risk_per_share = abs(entry_price - sl)
        risk_amount = equity * (cfg.risk_per_trade_pct / 100.0)
        shares = risk_amount / risk_per_share if risk_per_share > 0 else 0.0
        if cfg.max_leverage is not None:
            max_shares = (equity * cfg.max_leverage) / entry_price if entry_price > 0 else 0.0
            shares = min(shares, max_shares)

        sign = 1 if direction == "long" else -1
        pnl = shares * sign * (exit_price - entry_price) - cfg.commission_per_trade
        realized_risk_amount = shares * risk_per_share
        r_multiple = pnl / realized_risk_amount if realized_risk_amount > 0 else 0.0
        equity += pnl

        trades.append(
            Trade(
                date=ref_date,
                direction=direction,
                zone_high=zone_high,
                zone_low=zone_low,
                entry_time=df.index[entry_pos],
                entry_price=entry_price,
                sl=sl,
                tp=tp,
                exit_time=df.index[exit_pos],
                exit_price=exit_price,
                exit_reason=exit_reason,
                shares=shares,
                pnl=pnl,
                r_multiple=r_multiple,
            )
        )

    return pd.DataFrame([dataclasses.asdict(t) for t in trades])


def run_backtest_zone(df: pd.DataFrame, cfg: SessionZoneConfig) -> tuple[pd.DataFrame, pd.Series]:
    """Curva de equity por fecha de referencia -- misma construcción que
    src/backtest.py y src/simple_orb.py."""
    trades = generate_trades_zone(df, cfg)

    all_dates = pd.Index(sorted(set(df.index.date)))
    equity = cfg.starting_equity
    equity_by_date = {}

    pnl_by_date = trades.groupby("date")["pnl"].sum().to_dict() if not trades.empty else {}

    if len(all_dates):
        equity_by_date[all_dates[0] - pd.Timedelta(days=1)] = equity

    for d in all_dates:
        equity += pnl_by_date.get(d, 0.0)
        equity_by_date[d] = equity

    equity_curve = pd.Series(equity_by_date, name="equity")
    equity_curve.index = pd.to_datetime(equity_curve.index)
    equity_curve = equity_curve.sort_index()

    return trades, equity_curve


# Sesiones (hora de NY, convención estándar FX/futuros):
#   Asia (Tokio):  19:00-04:00   Londres: 03:00-12:00   NY: 09:30-16:00
# (NY usa el horario de apertura de acciones -- 09:30 -- porque es la
# convención ya validada en el resto de este proyecto, aunque NQ como
# futuro cotiza más horas.)
#
# `search_hours` = ventana después del fin de la zona en la que se busca
# el rompimiento. Para "primeros 30 min" es el resto de esa sesión (igual
# que la variante OR30 ya validada); para "últimos 30 min" se usa la
# misma duración que la sesión correspondiente, para que el horizonte de
# búsqueda sea comparable entre el primer y el último tramo de cada sesión.
ZONES: dict[str, dict] = {
    "asia_first30": dict(zone_start="19:00", zone_end="19:30", search_hours=8.5),
    "asia_last30": dict(zone_start="03:30", zone_end="04:00", search_hours=8.5),
    "london_first30": dict(zone_start="03:00", zone_end="03:30", search_hours=8.5),
    "london_last30": dict(zone_start="11:30", zone_end="12:00", search_hours=8.5),
    "ny_first30": dict(zone_start="09:30", zone_end="10:00", search_hours=6.0),  # = variante OR30 validada
    "ny_last30": dict(zone_start="15:30", zone_end="16:00", search_hours=6.0),
}
