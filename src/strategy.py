"""
Estrategia: NY Opening Range Breakout + confirmación de absorción con CVD (continuación).

Reglas implementadas (ver README.md para el detalle y los supuestos documentados):

1. Rango de apertura (OR): high/low de los primeros `or_minutes` (default 15)
   de la sesión de NY. Solo se valida si el volumen del OR es "considerable"
   respecto al volumen reciente (ver `_volume_surge_ok`) — así el rango de
   apertura solo se activa cuando el mercado realmente muestra la entrada de
   volumen típica de la apertura de NY, no en sesiones de baja liquidez.
2. Sesgo direccional: la primera vez que el precio toca/rompe el OR-high o el
   OR-low (cronológicamente) define el sesgo: rompe el high -> sesgo LONG,
   rompe el low -> sesgo SHORT.
3. Confirmación de entrada (absorción / CVD): tras el rompimiento se busca un
   pullback en contra. Dentro de ese pullback se detectan dos pivotes
   consecutivos del mismo tipo (lows si sesgo LONG, highs si sesgo SHORT).
   Si el PRECIO no confirma un nuevo extremo en el segundo pivote pero el CVD
   sí lo hace (diverge) -> absorción confirmada -> entrada A FAVOR del sesgo
   original (continuación), en la apertura de la vela siguiente al cierre
   que confirma el segundo pivote.
4. Stop loss: swing (high/low histórico) más cercano al precio de entrada,
   en el lado contrario a la operación.
5. Take profit: el SEGUNDO swing más cercano en el lado a favor de la
   operación (se salta el más cercano).
6. Si no se toca ni el SL ni el TP, se cierra en el cierre de la sesión
   (no se dejan posiciones overnight).
7. Filtro de POC semanal: se descarta la entrada si el precio de entrada
   queda demasiado cerca del Punto de Control (nivel de mayor volumen) del
   perfil de volumen de la SEMANA ANTERIOR completa — zona de rotación
   donde el mercado tiende a no tender con fuerza.
"""
from __future__ import annotations

import dataclasses
from typing import Optional

import numpy as np
import pandas as pd

from .config import Config
from .swings import Pivot, find_pivots, nearest_levels
from .volume_profile import get_prior_week_poc, weekly_poc


@dataclasses.dataclass
class Trade:
    date: object
    direction: str
    breakout_time: pd.Timestamp
    or_high: float
    or_low: float
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


def _session_day_groups(df: pd.DataFrame):
    """Devuelve lista de (date, start_pos, end_pos) posiciones enteras por día."""
    dates = df.index.date
    groups = []
    start = 0
    for i in range(1, len(df) + 1):
        if i == len(df) or dates[i] != dates[start]:
            groups.append((dates[start], start, i - 1))
            start = i
    return groups


def _opening_range(df: pd.DataFrame, start_pos: int, end_pos: int, or_minutes: int):
    day_open_time = df.index[start_pos]
    or_cutoff = day_open_time + pd.Timedelta(minutes=or_minutes)
    or_end_pos = start_pos
    while or_end_pos <= end_pos and df.index[or_end_pos] < or_cutoff:
        or_end_pos += 1
    if or_end_pos == start_pos:
        return None
    or_slice = df.iloc[start_pos:or_end_pos]
    return float(or_slice["high"].max()), float(or_slice["low"].min()), or_end_pos


def _volume_surge_ok(df: pd.DataFrame, start_pos: int, or_end_pos: int, cfg: Config) -> bool:
    """Exige que el rango de apertura venga acompañado de una entrada de
    volumen considerable (respecto al volumen reciente) antes de tomarlo
    como válido — así el "opening range" solo se activa cuando el mercado
    realmente muestra la explosión de participación típica de la apertura
    de NY, y no en aperturas de baja liquidez (feriados, sesiones flojas,
    datos con volumen plano) donde la premisa de la estrategia no aplica.
    """
    if not cfg.volume_filter_enabled:
        return True

    lookback_start = max(0, start_pos - cfg.volume_lookback_bars)
    if lookback_start == start_pos:
        return True  # no hay suficiente historia previa para estimar una línea base -> se deja pasar

    baseline = df["volume"].iloc[lookback_start:start_pos].mean()
    if baseline <= 0:
        return True

    or_volume = df["volume"].iloc[start_pos:or_end_pos].max()
    return bool(or_volume >= cfg.volume_multiplier * baseline)


def _near_weekly_poc(entry_price: float, entry_time: pd.Timestamp, pocs: dict, cfg: Config) -> bool:
    """True si `entry_price` queda demasiado cerca del Punto de Control
    (POC) del perfil de volumen de la SEMANA ANTERIOR completa — una zona
    de rotación/consolidación donde el mercado tiende a no tender con
    fuerza, así que una entrada justo ahí es de peor calidad y se descarta.
    """
    if not cfg.poc_filter_enabled:
        return False
    poc = get_prior_week_poc(pocs, entry_time)
    if poc != poc:  # nan -> no hay semana previa con datos, se deja pasar
        return False
    distance_pct = abs(entry_price - poc) / entry_price * 100.0
    return distance_pct < cfg.poc_min_distance_pct


def _find_breakout(df: pd.DataFrame, start_pos: int, end_pos: int, or_high: float, or_low: float):
    for pos in range(start_pos, end_pos + 1):
        bar = df.iloc[pos]
        hit_high = bar["high"] >= or_high
        hit_low = bar["low"] <= or_low
        if hit_high and hit_low:
            return None  # vela ambigua (toca ambos lados a la vez) -> se descarta el día
        if hit_high:
            return pos, "long"
        if hit_low:
            return pos, "short"
    return None


def _find_absorption_entry(
    df: pd.DataFrame,
    breakout_pos: int,
    direction: str,
    or_high: float,
    or_low: float,
    day_end_pos: int,
    cfg: Config,
):
    if cfg.max_bars_after_breakout:
        end_pos = min(day_end_pos, breakout_pos + cfg.max_bars_after_breakout)
    else:
        end_pos = day_end_pos

    if end_pos <= breakout_pos:
        return None

    invalidation_pos = None
    if cfg.invalidate_on_full_retrace:
        for pos in range(breakout_pos + 1, end_pos + 1):
            bar = df.iloc[pos]
            if direction == "long" and bar["low"] <= or_low:
                invalidation_pos = pos
                break
            if direction == "short" and bar["high"] >= or_high:
                invalidation_pos = pos
                break

    window_df = df.iloc[breakout_pos : end_pos + 1]
    pivots = find_pivots(window_df, window=cfg.pivot_lookback)

    kind_wanted = "low" if direction == "long" else "high"
    relevant = [p for p in pivots if p.kind == kind_wanted]
    if invalidation_pos is not None:
        relevant = [p for p in relevant if (breakout_pos + p.idx) < invalidation_pos]

    for i in range(1, len(relevant)):
        prev, curr = relevant[i - 1], relevant[i]
        abs_prev = breakout_pos + prev.idx
        abs_curr = breakout_pos + curr.idx
        cvd_prev = df["cvd"].iloc[abs_prev]
        cvd_curr = df["cvd"].iloc[abs_curr]

        if direction == "long":
            confirmed = (curr.price > prev.price) and (cvd_curr < cvd_prev)
        else:
            confirmed = (curr.price < prev.price) and (cvd_curr > cvd_prev)

        if confirmed:
            confirm_close_pos = abs_curr + cfg.pivot_lookback
            entry_pos = confirm_close_pos + 1
            if entry_pos > day_end_pos:
                continue  # no queda vela para ejecutar la entrada ese día
            return {
                "entry_pos": entry_pos,
                "prev_pivot": prev,
                "curr_pivot": curr,
            }
    return None


def _historical_swings(df: pd.DataFrame, entry_pos: int, cfg: Config) -> list[Pivot]:
    entry_time = df.index[entry_pos]
    lookback_start = entry_time - pd.Timedelta(days=cfg.swing_lookback_days)
    start_pos = df.index.searchsorted(lookback_start)
    hist = df.iloc[start_pos:entry_pos]  # excluye la vela de entrada (aún no cierra)
    if len(hist) < (2 * cfg.swing_fractal_window + 1):
        return []
    return find_pivots(hist, window=cfg.swing_fractal_window)


def _compute_sl_tp(df: pd.DataFrame, entry_pos: int, entry_price: float, direction: str, cfg: Config):
    pivots = _historical_swings(df, entry_pos, cfg)
    buffer = entry_price * cfg.sl_buffer_pct / 100.0

    if direction == "long":
        sl_candidates = nearest_levels(pivots, "low", entry_price, "below", n=1)
        tp_candidates = nearest_levels(pivots, "high", entry_price, "above", n=2)
        sl = (sl_candidates[0] - buffer) if sl_candidates else None
        tp = tp_candidates[1] if len(tp_candidates) >= 2 else (tp_candidates[0] if tp_candidates else None)
    else:
        sl_candidates = nearest_levels(pivots, "high", entry_price, "above", n=1)
        tp_candidates = nearest_levels(pivots, "low", entry_price, "below", n=2)
        sl = (sl_candidates[0] + buffer) if sl_candidates else None
        tp = tp_candidates[1] if len(tp_candidates) >= 2 else (tp_candidates[0] if tp_candidates else None)

    if sl is None:
        return None, None, "sin swing de SL disponible"

    risk = abs(entry_price - sl)
    if risk <= 0:
        return None, None, "riesgo <= 0"

    if tp is None:
        # fallback documentado: sin un segundo swing disponible, usar 2R
        tp = entry_price + 2 * risk if direction == "long" else entry_price - 2 * risk

    return sl, tp, None


def _apply_slippage(price: float, direction: str, side: str, slippage_bps: float) -> float:
    slip = slippage_bps / 10_000.0
    adverse_up = (direction == "long" and side == "entry") or (direction == "short" and side == "exit")
    return price * (1 + slip) if adverse_up else price * (1 - slip)


def _simulate_exit(df: pd.DataFrame, entry_pos: int, day_end_pos: int, direction: str, sl: float, tp: float):
    for pos in range(entry_pos, day_end_pos + 1):
        bar = df.iloc[pos]
        if direction == "long":
            hit_sl, hit_tp = bar["low"] <= sl, bar["high"] >= tp
        else:
            hit_sl, hit_tp = bar["high"] >= sl, bar["low"] <= tp

        if hit_sl and hit_tp:
            return pos, sl, "SL (vela ambigua, se asume SL primero por conservadurismo)"
        if hit_sl:
            return pos, sl, "SL"
        if hit_tp:
            return pos, tp, "TP"

    last = df.iloc[day_end_pos]
    return day_end_pos, float(last["close"]), "EOD (cierre de sesión)"


def generate_trades(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """df debe incluir columnas open/high/low/close/volume/delta/cvd,
    ya filtrado a horario de sesión e indexado en tz de NY."""
    trades: list[Trade] = []
    equity = cfg.starting_equity
    pocs = weekly_poc(df, cfg.poc_bin_pct) if cfg.poc_filter_enabled else {}

    for date, start_pos, end_pos in _session_day_groups(df):
        or_result = _opening_range(df, start_pos, end_pos, cfg.or_minutes)
        if or_result is None:
            continue
        or_high, or_low, or_end_pos = or_result
        if or_end_pos > end_pos:
            continue
        if not _volume_surge_ok(df, start_pos, or_end_pos, cfg):
            continue  # sin entrada de volumen considerable -> no se toma como apertura válida

        trades_today = 0
        search_pos = or_end_pos
        while trades_today < cfg.max_trades_per_day and search_pos <= end_pos:
            breakout = _find_breakout(df, search_pos, end_pos, or_high, or_low)
            if breakout is None:
                break
            breakout_pos, direction = breakout

            absorption = _find_absorption_entry(df, breakout_pos, direction, or_high, or_low, end_pos, cfg)
            if absorption is None:
                break  # no hubo confirmación de absorción ese día

            entry_pos = absorption["entry_pos"]
            raw_entry_price = float(df["open"].iloc[entry_pos])
            entry_price = _apply_slippage(raw_entry_price, direction, "entry", cfg.slippage_bps)

            if _near_weekly_poc(entry_price, df.index[entry_pos], pocs, cfg):
                break  # entrada demasiado cerca del POC semanal anterior -> se descarta el día

            sl, tp, reason = _compute_sl_tp(df, entry_pos, entry_price, direction, cfg)
            if sl is None:
                break

            exit_pos, raw_exit_price, exit_reason = _simulate_exit(df, entry_pos, end_pos, direction, sl, tp)
            exit_price = _apply_slippage(raw_exit_price, direction, "exit", cfg.slippage_bps)

            risk_per_share = abs(entry_price - sl)
            risk_amount = equity * (cfg.risk_per_trade_pct / 100.0)
            shares = risk_amount / risk_per_share if risk_per_share > 0 else 0.0

            sign = 1 if direction == "long" else -1
            pnl = shares * sign * (exit_price - entry_price) - cfg.commission_per_trade
            r_multiple = pnl / risk_amount if risk_amount > 0 else 0.0
            equity += pnl

            trades.append(
                Trade(
                    date=date,
                    direction=direction,
                    breakout_time=df.index[breakout_pos],
                    or_high=or_high,
                    or_low=or_low,
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
            trades_today += 1
            search_pos = exit_pos + 1

    return pd.DataFrame([dataclasses.asdict(t) for t in trades])
