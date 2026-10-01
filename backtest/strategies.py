"""
Las dos estrategias intradía, aplicadas al futuro NQ (proxy del US100 / Nasdaq-100).

Convenciones comunes
--------------------
* Velas de 1 min etiquetadas por su apertura: la vela i=0 es 09:30-09:31.
  El "precio a las HH:MM" es el cierre de la vela que termina en HH:MM
  (índice i-1). Ejemplo: precio de las 10:00 = Close[29].
* Ejecución por defecto "next_open": la señal se calcula con el precio de
  la marca y se ejecuta en la APERTURA de la vela siguiente (sin look-ahead).
  Alternativa "mark_close": se ejecuta al mismo precio que generó la señal
  (como en los papers; ligeramente optimista).
* Costos por lado y por contrato, en puntos de índice: 1 tick de slippage
  (0.25 pt) + comisión/fees ~2.50 USD (0.125 pt a 20 USD/pt) = 0.375 pt.
* Retornos expresados sobre el capital (AUM). Con apalancamiento 1x el
  nocional es igual al capital. El P&L de un futuro ya es retorno en exceso
  sobre la tasa libre de riesgo (el colateral gana el T-bill aparte), por lo
  que Sharpe/Sortino/alfa se calculan con rf = 0, que es lo correcto aquí.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

COST_PTS_PER_SIDE = 0.375


def _price_at(bars: pd.DataFrame, minute_idx: int) -> float:
    """Precio en la marca que cae `minute_idx` minutos después de las 09:30."""
    return float(bars.Close.iloc[minute_idx - 1])


# ---------------------------------------------------------------------------
# 1) Zarattini, Aziz & Barbon (2024) - "Beat the Market: An Effective Intraday
#    Momentum Strategy for S&P500 ETF (SPY)", SSRN 4824172.
# ---------------------------------------------------------------------------
def noise_band_momentum(data, lookback: int = 14, vol_mult: float = 1.0, sizing: str = "voltarget",
                        target_vol: float = 0.02, max_lev: float = 4.0, execution: str = "next_open",
                        cost_pts: float = COST_PTS_PER_SIDE, check_every: int = 30):
    """
    Bandas de ruido:  UB_t = max(Open, PrevClose) * (1 + vm * sigma_t)
                      LB_t = min(Open, PrevClose) * (1 - vm * sigma_t)
    sigma_t = promedio de |Close_t / Open - 1| en el MISMO minuto t de los
    `lookback` días operables anteriores.
    Cada 30 min (10:00 ... 15:30): largo si precio > UB, corto si < LB.
    Trailing stop: largo sale si precio <= max(UB, VWAP); corto si >= min(LB, VWAP).
    Todo se cierra a las 16:00. Sin cierre previo válido (día de roll) se usa solo Open.
    Sizing "voltarget" (paper): apalancamiento = min(max_lev, target_vol / sigma_diaria_14d).
    """
    daily = data.daily
    days = [d for d in daily.index if daily.at[d, "tradable"]]
    move = np.vstack([np.abs(data.bars[d].Close.values / data.bars[d].Open.values[0] - 1) for d in days])
    rets_cc = daily.loc[days, "ret_cc"]

    out, trades = [], []
    for k, d in enumerate(days):
        if k < lookback:
            continue
        b = data.bars[d]
        o, c, op, vwap = b.Open.values[0], b.Close.values, b.Open.values, b.VWAP.values
        sigma = move[k - lookback:k].mean(axis=0)
        pc = daily.at[d, "prev_close"]
        hi_ref = max(o, pc) if np.isfinite(pc) else o
        lo_ref = min(o, pc) if np.isfinite(pc) else o
        ub = hi_ref * (1 + vol_mult * sigma)
        lb = lo_ref * (1 - vol_mult * sigma)

        if sizing == "voltarget":
            past = rets_cc.iloc[:k].dropna().tail(lookback)
            sd = past.std(ddof=1)
            lev = min(max_lev, target_vol / sd) if sd > 0 else 1.0
        else:
            lev = 1.0

        pos, entry_px, entry_t, pnl_pts, cost = 0, np.nan, None, 0.0, 0.0
        for m in range(check_every, RTH_END, check_every):  # 10:00 .. 15:30
            i = m - 1
            p = c[i]
            new = pos
            if pos == 1 and p <= max(ub[i], vwap[i]):
                new = 0
            elif pos == -1 and p >= min(lb[i], vwap[i]):
                new = 0
            if new == 0:
                if p > ub[i]:
                    new = 1
                elif p < lb[i]:
                    new = -1
            if new != pos:
                px = op[m] if execution == "next_open" else p
                t = b.index[m] if execution == "next_open" else b.index[i] + pd.Timedelta(minutes=1)
                if pos != 0:
                    pnl_pts += pos * (px - entry_px)
                    trades.append(dict(strategy="S1", date=d, side=pos, entry_time=entry_t, entry=entry_px,
                                       exit_time=t, exit=px, ret=lev * (pos * (px - entry_px) - 2 * cost_pts) / o))
                cost += abs(new - pos) * cost_pts
                pos, entry_px, entry_t = new, px, t
        if pos != 0:
            px = c[-1]
            pnl_pts += pos * (px - entry_px)
            cost += cost_pts
            trades.append(dict(strategy="S1", date=d, side=pos, entry_time=entry_t, entry=entry_px,
                               exit_time=b.index[-1] + pd.Timedelta(minutes=1), exit=px,
                               ret=lev * (pos * (px - entry_px) - 2 * cost_pts) / o))
        out.append(dict(date=d, ret=lev * (pnl_pts - cost) / o, gross=lev * pnl_pts / o, lev=lev))
    return pd.DataFrame(out).set_index("date"), pd.DataFrame(trades)


RTH_END = 390


# ---------------------------------------------------------------------------
# 2) Gao, Han, Li & Zhou (2018) - "Market Intraday Momentum", JFE / SSRN 2552752.
# ---------------------------------------------------------------------------
def first_half_hour_momentum(data, vix_min: float | None = 20.0, first_def: str = "prev_close",
                             execution: str = "next_open", cost_pts: float = COST_PTS_PER_SIDE,
                             start_date=None):
    """
    r1  = rendimiento de la primera media hora. Definición del paper: cierre
          previo (16:00 de ayer) -> 10:00. Variante "open": 09:30 -> 10:00.
    r12 = rendimiento de la penúltima media hora, 15:00 -> 15:30.
    Si r1 > 0 y r12 > 0: largo 15:30 -> 16:00; si ambos < 0: corto; si no, plano.
    Filtro VIX: solo opera si el cierre del VIX del día anterior >= vix_min.
    """
    daily = data.daily
    out, trades = [], []
    for d in daily.index:
        if not daily.at[d, "tradable"] or (start_date is not None and d < start_date):
            continue
        b = data.bars[d]
        c = b.Close.values
        if first_def == "prev_close":
            base = daily.at[d, "prev_close"]
            if not np.isfinite(base):  # día de roll: el cierre previo es de otro contrato
                base = b.Open.values[0]
        else:
            base = b.Open.values[0]
        r1 = _price_at(b, 30) / base - 1
        r12 = _price_at(b, 360) / _price_at(b, 330) - 1
        side = 1 if (r1 > 0 and r12 > 0) else -1 if (r1 < 0 and r12 < 0) else 0
        vix = daily.at[d, "vix_prev_close"]
        if vix_min is not None and not (vix >= vix_min):
            side = 0
        ret = gross = 0.0
        if side != 0:
            entry = b.Open.values[360] if execution == "next_open" else _price_at(b, 360)
            exit_ = c[-1]
            gross = side * (exit_ - entry) / entry
            ret = gross - 2 * cost_pts / entry
            trades.append(dict(strategy="S2", date=d, side=side, entry_time=b.index[360], entry=entry,
                               exit_time=b.index[-1] + pd.Timedelta(minutes=1), exit=exit_, ret=ret,
                               r1=r1, r12=r12, vix_prev=vix))
        out.append(dict(date=d, ret=ret, gross=gross, lev=1.0))
    return pd.DataFrame(out).set_index("date"), pd.DataFrame(trades)
