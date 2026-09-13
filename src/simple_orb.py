"""
Estrategia alternativa: Opening Range Breakout (ORB) CLÁSICO, SIN la capa
de confirmación por absorción de CVD.

Motivación: tras probar múltiples variantes de ORB + absorción CVD
(continuación) sobre 6 meses reales de QQQ -- con y sin filtro de volumen,
filtro de liquidez, banda de desviación estándar semanal -- ninguna
combinación superó profit factor 1.0 de forma consistente (ver README.md).
El CVD usado es una APROXIMACIÓN a partir de velas OHLCV (no hay datos de
tick real), y es razonable sospechar que esa señal aproximada mete ruido
en vez de aportar una edge genuina. Esta variante prueba una hipótesis
distinta y más simple: quizás el rompimiento del rango de apertura por sí
solo, ejecutado como una orden stop (sin esperar confirmación de
absorción), con un stop y un take profit simples, tiene mejor
comportamiento.

Reglas:

1. Rango de apertura (OR): high/low de los primeros `or_minutes` de la
   sesión. Opcionalmente exige un repunte de volumen (mismo filtro que la
   estrategia principal, ver `_volume_surge_ok` en `src/strategy.py`).
2. Entrada: al primer rompimiento del OR-high o OR-low, se asume una orden
   stop ya colocada en ese nivel -> se rellena en el nivel mismo, o en el
   open de la vela si esta abre más allá del nivel (gap).
3. Filtro de tendencia opcional (`trend_filter_enabled`): solo LONG si el
   día anterior cerró por encima de su apertura (día alcista); solo SHORT
   si cerró por debajo (día bajista). Este es un filtro citado en la
   literatura de ORB clásico como potenciador de edge.
3b. Modo de dirección (`direction_mode`): "breakout" (default, continuación
   -- se opera A FAVOR del rompimiento) o "fade" (reversión -- se opera EN
   CONTRA: short si rompe el high, long si rompe el low, apostando a que
   fue una barrida de liquidez/falso rompimiento). El SL en modo "fade"
   con `sl_mode="or_opposite"` se ancla en el extremo real de la vela que
   rompió el rango (no en el nivel del OR, que ya quedó superado), para no
   saltar en la misma vela de entrada.
4. Stop loss, dos modos seleccionables (`sl_mode`):
   - "or_opposite": el lado contrario del rango de apertura (el clásico
     "riesgo = ancho del OR").
   - "liquidity": el swing histórico más cercano en contra que además sea
     un pool de liquidez genuino (mismo filtro `_is_liquidity_level` /
     `_historical_swings` que la estrategia principal, reutilizados aquí
     por duck typing sobre los campos de `SimpleORBConfig`).
5. Take profit, tres modos seleccionables (`tp_mode`):
   - "r_multiple" (default): múltiplo fijo de R (`tp_r_multiple`) sobre el
     riesgo definido por el SL -- no depende de swings futuros ni de absorción.
   - "opposite_extreme": el lado OPUESTO del rango de referencia (ver
     `range_source` abajo) -- el objetivo estructural clásico de ICT/SMC
     de "barrer un lado, apuntar al otro" (p.ej. barre el high del día
     anterior, el objetivo es el low del día anterior).
   - "poc": el Punto de Control (POC) de la sesión anterior -- el nivel de
     precio con más volumen acumulado (ver `_session_poc`), como objetivo
     alternativo/más cercano al "opposite_extreme".
   En "opposite_extreme"/"poc", si el nivel objetivo ya quedó del lado
   equivocado del precio de entrada (sin recorrido a favor), no hay trade
   ese día.
6. Rango de referencia (`range_source`): de dónde salen el high/low que
   definen el rompimiento (y, en modo "fade", cuál lado se barre):
   - "opening_range" (default): los primeros `or_minutes` de la sesión
     (igual que las reglas 1-2 originales).
   - "prev_session": el high/low de TODA la sesión de trading anterior
     (PDH/PDL, "previous day high/low" -- un concepto de liquidez ICT/SMC
     clásico: se asume que hay stops/órdenes reales descansando ahí). No
     usa `or_minutes` ni el filtro de volumen (no hay "apertura" que
     medir); la búsqueda de rompimiento arranca desde el open de la
     sesión.
7. Si no se toca ni el SL ni el TP, se cierra al cierre de la sesión.

Esta es una hipótesis a validar, no una promesa de que "funciona": se
prueba con un split honesto entrenamiento/prueba (ver
`scripts/run_simple_orb_grid.py`) para evitar sobreajustar los parámetros
al total de los 6 meses reales disponibles.
"""
from __future__ import annotations

import dataclasses
from typing import Optional

import numpy as np
import pandas as pd

from .data import restrict_to_session
from .strategy import (
    _apply_slippage,
    _historical_swings,
    _is_liquidity_level,
    _opening_range,
    _session_day_groups,
    _simulate_exit,
    _volume_surge_ok,
)
from .swings import nearest_pivots


@dataclasses.dataclass
class SimpleORBConfig:
    session_open: str = "09:30"
    session_close: str = "16:00"
    session_only: bool = True

    or_minutes: int = 15

    range_source: str = "opening_range"  # "opening_range" | "prev_session" (PDH/PDL)

    volume_filter_enabled: bool = True
    volume_lookback_bars: int = 20
    volume_multiplier: float = 1.5

    trend_filter_enabled: bool = False

    direction_mode: str = "breakout"  # "breakout" (continuación) | "fade" (reversión al toque del OR)

    sl_mode: str = "or_opposite"  # "or_opposite" | "liquidity"
    tp_mode: str = "r_multiple"  # "r_multiple" | "opposite_extreme" | "poc"
    tp_r_multiple: float = 2.0
    poc_bins: int = 30  # bins del histograma de volumen usado para aproximar el POC de la sesión anterior

    # solo se usan si sl_mode == "liquidity" (reutilizan la lógica de src/strategy.py)
    liquidity_filter_enabled: bool = True
    liquidity_lookback_bars: int = 20
    liquidity_multiplier: float = 1.5
    swing_fractal_window: int = 3
    swing_lookback_days: int = 5

    sl_buffer_pct: float = 0.03
    starting_equity: float = 10_000.0
    risk_per_trade_pct: float = 1.0
    max_leverage: Optional[float] = None
    # Límite de exposición: si el SL queda muy cerca (p.ej. anclado en la
    # mecha real de la vela de rompimiento, en modo "fade"), arriesgar
    # `risk_per_trade_pct` puede exigir una posición nocional gigante
    # (decenas de veces el equity) -- irrealizable sin apalancamiento
    # extremo. `max_leverage` (nocional / equity) limita el tamaño de la
    # posición; cuando se activa, el riesgo real de ese trade queda por
    # debajo de `risk_per_trade_pct` y el R-multiple se recalcula sobre el
    # riesgo real asumido (no sobre el nominal). None = sin límite (modelo
    # de sizing "R puro", como el resto del proyecto).
    max_trades_per_day: int = 1
    slippage_bps: float = 1.0
    commission_per_trade: float = 0.0


@dataclasses.dataclass
class Trade:
    date: object
    direction: str
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


def _find_breakout_fill(df: pd.DataFrame, start_pos: int, end_pos: int, or_high: float, or_low: float):
    """Como `_find_breakout` en src/strategy.py, pero además calcula el
    precio de relleno asumiendo una orden stop colocada en el nivel del OR:
    se rellena en el nivel mismo, o en el open de la vela si esta abre más
    allá del nivel (gap más realista que asumir el nivel exacto siempre).
    También devuelve el high/low reales de la vela de rompimiento (se
    necesitan para anclar el SL en modo "fade")."""
    for pos in range(start_pos, end_pos + 1):
        bar = df.iloc[pos]
        hit_high = bar["high"] >= or_high
        hit_low = bar["low"] <= or_low
        if hit_high and hit_low:
            return None  # vela ambigua -> se descarta el día
        if hit_high:
            fill = max(or_high, float(bar["open"]))
            return pos, "long", fill, float(bar["high"]), float(bar["low"])
        if hit_low:
            fill = min(or_low, float(bar["open"]))
            return pos, "short", fill, float(bar["high"]), float(bar["low"])
    return None


def _compute_sl_tp_simple(
    df: pd.DataFrame,
    entry_pos: int,
    entry_price: float,
    direction: str,
    sl_anchor_price: float,
    cfg: SimpleORBConfig,
):
    """`sl_anchor_price` es el nivel a partir del cual se calcula el SL en
    modo "or_opposite": en modo "breakout" es el lado contrario del OR
    (or_low para long / or_high para short); en modo "fade" es el extremo
    real de la vela que rompió el rango (ya que el nivel del OR quedó
    superado y no serviría como stop)."""
    buffer = entry_price * cfg.sl_buffer_pct / 100.0

    if cfg.sl_mode == "or_opposite":
        sl = (sl_anchor_price - buffer) if direction == "long" else (sl_anchor_price + buffer)
    elif cfg.sl_mode == "liquidity":
        pivots = _historical_swings(df, entry_pos, cfg)
        sl_kind = "low" if direction == "long" else "high"
        sl_side = "below" if direction == "long" else "above"
        sl_pivot_candidates = nearest_pivots(pivots, sl_kind, entry_price, sl_side, n=len(pivots) or 1)
        sl_pivot = next((p for p in sl_pivot_candidates if _is_liquidity_level(df, p.idx, cfg)), None)
        if sl_pivot is None:
            return None, None, "sin swing de SL con liquidez suficiente"
        sl = (sl_pivot.price - buffer) if direction == "long" else (sl_pivot.price + buffer)
    else:
        raise ValueError(f"sl_mode desconocido: {cfg.sl_mode!r}")

    risk = abs(entry_price - sl)
    if risk <= 0:
        return None, None, "riesgo <= 0"

    tp = entry_price + cfg.tp_r_multiple * risk if direction == "long" else entry_price - cfg.tp_r_multiple * risk
    return sl, tp, None


def _prior_day_trend(df: pd.DataFrame, day_groups: list[tuple]) -> dict:
    """date -> 'up'/'down'/None (None para el primer día, sin referencia)."""
    trend = {}
    for i, (date, start_pos, end_pos) in enumerate(day_groups):
        if i == 0:
            trend[date] = None
            continue
        _, prev_start, prev_end = day_groups[i - 1]
        prev_open = float(df["open"].iloc[prev_start])
        prev_close = float(df["close"].iloc[prev_end])
        trend[date] = "up" if prev_close > prev_open else "down"
    return trend


def _session_poc(session_df: pd.DataFrame, n_bins: int = 30) -> Optional[float]:
    """Aproxima el Punto de Control (POC) de una sesión: el nivel de precio
    con más volumen acumulado. Sin datos de tick real, se usa un histograma
    de `n_bins` sobre el rango high-low de la sesión, asignando el volumen
    de cada vela al bin de su precio típico (H+L+C)/3 -- la misma
    aproximación estándar que el resto del proyecto usa para CVD/volumen
    cuando no hay order flow real."""
    if session_df.empty:
        return None
    lo = float(session_df["low"].min())
    hi = float(session_df["high"].max())
    if hi <= lo:
        return None
    typical = (session_df["high"] + session_df["low"] + session_df["close"]) / 3.0
    bin_edges = np.linspace(lo, hi, n_bins + 1)
    bin_idx = np.clip(np.digitize(typical.values, bin_edges) - 1, 0, n_bins - 1)
    vol_per_bin = np.zeros(n_bins)
    np.add.at(vol_per_bin, bin_idx, session_df["volume"].values)
    best_bin = int(np.argmax(vol_per_bin))
    return float((bin_edges[best_bin] + bin_edges[best_bin + 1]) / 2.0)


def _prev_session_ref(df: pd.DataFrame, day_groups: list[tuple], poc_bins: int = 30) -> dict:
    """date -> (prev_high, prev_low, prev_poc) de la sesión de trading
    INMEDIATAMENTE anterior con datos (PDH/PDL + POC aproximado de esa
    sesión). Ausente para el primer día (sin referencia)."""
    ref = {}
    for i, (date, start_pos, end_pos) in enumerate(day_groups):
        if i == 0:
            continue
        _, prev_start, prev_end = day_groups[i - 1]
        prev_slice = df.iloc[prev_start : prev_end + 1]
        prev_high = float(prev_slice["high"].max())
        prev_low = float(prev_slice["low"].min())
        prev_poc = _session_poc(prev_slice, n_bins=poc_bins)
        ref[date] = (prev_high, prev_low, prev_poc)
    return ref


def generate_trades_simple(df: pd.DataFrame, cfg: SimpleORBConfig) -> pd.DataFrame:
    """df debe incluir columnas open/high/low/close/volume, indexado en la
    tz de la sesión (no requiere CVD)."""
    trades: list[Trade] = []
    equity = cfg.starting_equity

    day_groups = _session_day_groups(df)
    trend_by_date = _prior_day_trend(df, day_groups) if cfg.trend_filter_enabled else {}

    need_prev_session = cfg.range_source == "prev_session" or cfg.tp_mode == "poc"
    prev_session_by_date = _prev_session_ref(df, day_groups, poc_bins=cfg.poc_bins) if need_prev_session else {}

    for date, start_pos, end_pos in day_groups:
        pref = prev_session_by_date.get(date) if need_prev_session else None
        poc_ref = pref[2] if pref is not None else None

        if cfg.range_source == "opening_range":
            or_result = _opening_range(df, start_pos, end_pos, cfg.or_minutes)
            if or_result is None:
                continue
            or_high, or_low, or_end_pos = or_result
            if or_end_pos > end_pos:
                continue
            if cfg.volume_filter_enabled and not _volume_surge_ok(df, start_pos, or_end_pos, cfg):
                continue
            search_start = or_end_pos
        elif cfg.range_source == "prev_session":
            if pref is None:
                continue  # primer día del historial -> sin sesión anterior de referencia
            or_high, or_low, _ = pref
            if or_high <= or_low:
                continue
            search_start = start_pos  # sin "apertura" que esperar: el rango ya existe desde ayer
        else:
            raise ValueError(f"range_source desconocido: {cfg.range_source!r}")

        trades_today = 0
        search_pos = search_start
        while trades_today < cfg.max_trades_per_day and search_pos <= end_pos:
            breakout = _find_breakout_fill(df, search_pos, end_pos, or_high, or_low)
            if breakout is None:
                break
            breakout_pos, raw_direction, raw_fill_price, bar_high, bar_low = breakout

            if cfg.direction_mode == "fade":
                direction = "short" if raw_direction == "long" else "long"
                sl_anchor = bar_high if direction == "short" else bar_low
            else:
                direction = raw_direction
                sl_anchor = or_low if direction == "long" else or_high

            if cfg.trend_filter_enabled:
                trend = trend_by_date.get(date)
                if (direction == "long" and trend != "up") or (direction == "short" and trend != "down"):
                    break  # el sesgo de tendencia del día anterior no coincide -> se descarta el día

            entry_pos = breakout_pos
            entry_price = _apply_slippage(raw_fill_price, direction, "entry", cfg.slippage_bps)

            sl, tp, reason = _compute_sl_tp_simple(df, entry_pos, entry_price, direction, sl_anchor, cfg)
            if sl is None:
                break

            if cfg.tp_mode == "opposite_extreme":
                # el objetivo es el lado del rango que NO se rompió -- se define por
                # `raw_direction` (qué lado se rompió), no por `direction` (que en modo
                # "fade" ya está invertida respecto al lado roto)
                candidate_tp = or_low if raw_direction == "long" else or_high
                if (direction == "long" and candidate_tp <= entry_price) or (
                    direction == "short" and candidate_tp >= entry_price
                ):
                    break  # el lado opuesto del rango ya quedó del lado equivocado -> sin objetivo válido
                tp = candidate_tp
            elif cfg.tp_mode == "poc":
                if poc_ref is None:
                    break  # sin POC de la sesión anterior disponible (p.ej. primer día)
                if (direction == "long" and poc_ref <= entry_price) or (
                    direction == "short" and poc_ref >= entry_price
                ):
                    break  # el POC ya quedó del lado equivocado -> sin objetivo válido
                tp = poc_ref
            # else "r_multiple": se deja el tp calculado por _compute_sl_tp_simple

            exit_pos, raw_exit_price, exit_reason = _simulate_exit(df, entry_pos, end_pos, direction, sl, tp)
            exit_price = _apply_slippage(raw_exit_price, direction, "exit", cfg.slippage_bps)

            risk_per_share = abs(entry_price - sl)
            risk_amount = equity * (cfg.risk_per_trade_pct / 100.0)
            shares = risk_amount / risk_per_share if risk_per_share > 0 else 0.0
            if cfg.max_leverage is not None:
                max_shares = (equity * cfg.max_leverage) / entry_price if entry_price > 0 else 0.0
                shares = min(shares, max_shares)

            sign = 1 if direction == "long" else -1
            pnl = shares * sign * (exit_price - entry_price) - cfg.commission_per_trade
            realized_risk_amount = shares * risk_per_share  # riesgo real tras el posible cap de leverage
            r_multiple = pnl / realized_risk_amount if realized_risk_amount > 0 else 0.0
            equity += pnl

            trades.append(
                Trade(
                    date=date,
                    direction=direction,
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


def run_backtest_simple(df: pd.DataFrame, cfg: SimpleORBConfig) -> tuple[pd.DataFrame, pd.Series]:
    """Igual que `src.backtest.run_backtest` pero para la variante sin CVD."""
    if cfg.session_only:
        df = restrict_to_session(df, cfg.session_open, cfg.session_close)

    trades = generate_trades_simple(df, cfg)

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
