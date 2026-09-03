"""
Generadores de mercados SINTÉTICOS para pruebas de robustez del backtest.

Tres datasets con procesos generadores fundamentalmente distintos, pensados
para estresar la estrategia bajo distintos supuestos de microestructura de
mercado — no para estimar su rentabilidad real (para eso hace falta el CSV
de datos reales, ver README.md).

Dataset A — "Tradicional": Geometric Brownian Motion + GARCH(1,1).
    El modelo estándar de libro de texto en finanzas cuantitativas: retornos
    ~condicionalmente Gaussianos, con clustering de volatilidad vía GARCH
    (el mecanismo "tradicional" de heterocedasticidad condicional). Colas
    relativamente delgadas, sin memoria larga, sin estructura multifractal.

Dataset B — "Sistemas complejos / criticidad auto-organizada (SOC)":
    Combina dos mecanismos tomados de la física de sistemas críticos:
      1. Cascada multiplicativa multifractal (estilo Markov-Switching
         Multifractal de Calvet & Fisher): la volatilidad es el producto de
         K componentes binarios que conmutan a distintas escalas temporales
         (rápida -> lenta), generando una jerarquía de volatilidad auto-
         similar típica de series multifractales.
      2. Proceso de Hawkes (auto-excitante) con magnitudes de cola pesada
         (Pareto/power-law) para los "eventos" — esta es exactamente la
         representación matemática que usa la propia literatura de
         criticidad auto-organizada para: terremotos (modelo ETAS),
         avalanchas, incendios forestales, apagones en cascada, y también
         crashes/clustering de volatilidad en mercados financieros. Un
         evento puede gatillar nuevos eventos (auto-excitación = avalancha
         que se propaga), con tamaños que siguen ley de potencias (análogo
         a Gutenberg-Richter / distribución de tamaño de avalanchas).
    Resultado: colas pesadas, clustering de eventos en el tiempo,
    volatilidad multifractal — justo lo opuesto al supuesto Gaussiano de A.

Dataset C — "Regime-switching multifractal + SOC" (combina A y B):
    Cadena de Markov de 2 estados (CALMA / CRÍTICO) que alterna entre la
    dinámica de A (calma) y la de B (crítico), con alta persistencia y
    episodios críticos más cortos y agudos que los tramos de calma — igual
    que ciclos reales de mercado (largos períodos tranquilos, interrumpidos
    por crisis breves y violentas). Ambos procesos subyacentes (GARCH y
    cascada+Hawkes) siguen evolucionando en segundo plano incluso cuando no
    están "activos", para que el retorno a un régimen no sea discontinuo.

Todas las funciones devuelven un DataFrame OHLCV en el mismo formato que
`src/synthetic.py` (índice tz-aware America/New_York, columnas
open/high/low/close/volume), compatible con `src/backtest.run_backtest`.
"""
from __future__ import annotations

from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Utilidades compartidas: calendario de sesión + construcción de velas OHLCV
# a partir de una serie de retornos por vela.
# ---------------------------------------------------------------------------

def _session_timestamps(months_back: int, interval_minutes: int, tz: str) -> pd.DatetimeIndex:
    end_date = pd.Timestamp.now(tz=ZoneInfo(tz)).normalize()
    start_date = end_date - pd.DateOffset(months=months_back)
    trading_days = pd.bdate_range(start_date, end_date)  # aproximación: días hábiles (sin festivos US)
    bars_per_day = int(390 / interval_minutes)  # sesión 9:30-16:00 = 390 min

    stamps = []
    for day in trading_days:
        day_open = day + pd.Timedelta(hours=9, minutes=30)
        stamps.extend(day_open + pd.Timedelta(minutes=interval_minutes * b) for b in range(bars_per_day))
    idx = pd.DatetimeIndex(stamps)
    return idx.tz_localize(ZoneInfo(tz)) if idx.tz is None else idx.tz_convert(ZoneInfo(tz))


def _bars_from_returns(
    timestamps: pd.DatetimeIndex,
    returns: np.ndarray,
    intrabar_vol: np.ndarray,
    volume: np.ndarray,
    start_price: float,
    gap_std: float,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Construye OHLC a partir de una serie de retornos por vela + volatilidad
    intrabar (usada para el rango high/low) y volumen, ya simulados."""
    n = len(timestamps)
    dates = timestamps.date
    price = start_price

    o = np.empty(n)
    h = np.empty(n)
    l = np.empty(n)
    c = np.empty(n)

    for i in range(n):
        if i == 0 or dates[i] != dates[i - 1]:
            price *= 1 + rng.normal(0, gap_std)  # gap overnight al inicio de cada día
        op = price
        cl = op * (1 + returns[i])
        noise = abs(rng.normal(0, max(intrabar_vol[i], 1e-6) * 0.6))
        hi = max(op, cl) * (1 + noise)
        lo = min(op, cl) * (1 - noise)
        o[i], h[i], l[i], c[i] = op, hi, lo, cl
        price = cl

    df = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": volume}, index=timestamps)
    return df


def _pareto_sample(u: float, xm: float, alpha: float) -> float:
    """Inversa de la CDF de Pareto: P(X>x) = (xm/x)^alpha, x>=xm."""
    return xm * (1.0 - u) ** (-1.0 / alpha)


# ---------------------------------------------------------------------------
# Dataset A: GBM + GARCH(1,1) ("tradicional")
# ---------------------------------------------------------------------------

def generate_dataset_a(
    months_back: int = 6,
    interval_minutes: int = 5,
    start_price: float = 480.0,
    tz: str = "America/New_York",
    mu: float = 0.0,
    omega: float = 2e-7,
    alpha_garch: float = 0.08,
    beta_garch: float = 0.90,
    gap_std: float = 0.0015,
    seed: int = 101,
) -> pd.DataFrame:
    """Mercado sintético tradicional: GBM con volatilidad GARCH(1,1)."""
    rng = np.random.default_rng(seed)
    ts = _session_timestamps(months_back, interval_minutes, tz)
    n = len(ts)

    returns = np.empty(n)
    sigma = np.empty(n)
    volume = np.empty(n)

    sigma2 = omega / max(1e-9, (1 - alpha_garch - beta_garch))  # varianza incondicional como semilla
    prev_r2 = sigma2
    for i in range(n):
        sigma2 = omega + alpha_garch * prev_r2 + beta_garch * sigma2
        s = np.sqrt(sigma2)
        eps = rng.normal()
        r = mu + s * eps
        returns[i] = r
        sigma[i] = s
        prev_r2 = r * r
        volume[i] = max(1.0, rng.lognormal(mean=9.0, sigma=0.4) * (1 + 2.0 * abs(r) / max(s, 1e-9) * 0.05))

    return _bars_from_returns(ts, returns, sigma, volume, start_price, gap_std, rng)


# ---------------------------------------------------------------------------
# Dataset B: cascada multifractal (MSM-like) + Hawkes power-law ("SOC")
# ---------------------------------------------------------------------------

def _msm_step(multipliers: np.ndarray, switch_probs: np.ndarray, m_low: float, m_high: float, rng: np.random.Generator) -> None:
    """Un paso de la cascada multiplicativa: cada componente conmuta con su
    propia probabilidad (independiente) entre {m_low, m_high}."""
    draws = rng.random(len(multipliers))
    switch = draws < switch_probs
    new_vals = np.where(rng.random(len(multipliers)) < 0.5, m_low, m_high)
    multipliers[switch] = new_vals[switch]


def generate_dataset_b(
    months_back: int = 6,
    interval_minutes: int = 5,
    start_price: float = 480.0,
    tz: str = "America/New_York",
    mu: float = 0.0,
    sigma_base: float = 0.003,
    k_cascade: int = 6,
    p1: float = 0.25,
    decay: float = 0.45,
    m_low: float = 0.5,
    m_high: float = 1.5,
    hawkes_lambda0: float = 0.005,
    hawkes_alpha: float = 0.15,
    hawkes_beta: float = 0.35,
    hawkes_ratio_cap: float = 5.0,
    pareto_xm: float = 0.0025,
    pareto_alpha: float = 2.6,
    gap_std: float = 0.003,
    seed: int = 202,
) -> pd.DataFrame:
    """Mercado sintético de criticidad auto-organizada / multifractal.

    Volatilidad = cascada multiplicativa multifractal (MSM-like).
    Shocks = proceso de Hawkes auto-excitante con magnitudes Pareto (misma
    representación matemática que terremotos/avalanchas/apagones/incendios).
    """
    rng = np.random.default_rng(seed)
    ts = _session_timestamps(months_back, interval_minutes, tz)
    n = len(ts)

    switch_probs = np.array([min(0.5, p1 * (decay ** i)) for i in range(k_cascade)])
    multipliers = rng.choice([m_low, m_high], size=k_cascade)

    returns = np.empty(n)
    sigma_series = np.empty(n)
    volume = np.empty(n)
    shock_flag = np.zeros(n, dtype=bool)

    hawkes_intensity_excess = 0.0  # componente auto-excitante de la intensidad (decae exponencialmente)

    for i in range(n):
        _msm_step(multipliers, switch_probs, m_low, m_high, rng)
        sigma_t = sigma_base * np.sqrt(np.prod(multipliers))
        sigma_series[i] = sigma_t

        hawkes_intensity_excess *= np.exp(-hawkes_beta)  # decaimiento del kernel exponencial (1 vela = 1 paso)
        lam = hawkes_lambda0 + hawkes_intensity_excess

        shock = 0.0
        if rng.random() < min(0.98, lam):
            u = rng.random()
            magnitude = _pareto_sample(u, pareto_xm, pareto_alpha)
            magnitude = min(magnitude, pareto_xm * 40)  # tope para evitar valores absurdos de cola extrema
            sign = 1.0 if rng.random() < 0.5 else -1.0
            shock = sign * magnitude
            # auto-excitación acotada (ratio_cap): sin esto el feedback se satura y el
            # "avalanche" deja de ser un evento raro y agrupado para volverse casi permanente
            hawkes_intensity_excess += hawkes_alpha * min(magnitude / pareto_xm, hawkes_ratio_cap)
            shock_flag[i] = True

        eps = rng.normal()
        r = mu + sigma_t * eps + shock
        returns[i] = r

        vol_base = rng.lognormal(mean=9.0, sigma=0.4)
        volume[i] = max(1.0, vol_base * (1 + (6.0 if shock_flag[i] else 0.0) + 3.0 * abs(r) / max(sigma_t, 1e-9) * 0.05))

    return _bars_from_returns(ts, returns, sigma_series, volume, start_price, gap_std, rng)


# ---------------------------------------------------------------------------
# Dataset C: regime-switching entre A (calma) y B (crítico)
# ---------------------------------------------------------------------------

def generate_dataset_c(
    months_back: int = 6,
    interval_minutes: int = 5,
    start_price: float = 480.0,
    tz: str = "America/New_York",
    p_enter_critical: float = 0.003,
    p_exit_critical: float = 0.02,
    seed: int = 303,
    dataset_a_kwargs: dict | None = None,
    dataset_b_kwargs: dict | None = None,
) -> pd.DataFrame:
    """Mercado sintético con regime-switching entre dinámica 'calma' (A) y
    'crítica' (B), vía una cadena de Markov de 2 estados con alta
    persistencia (episodios críticos más cortos y agudos que los de calma).
    """
    rng = np.random.default_rng(seed)
    ts = _session_timestamps(months_back, interval_minutes, tz)
    n = len(ts)

    a_kw = dict(mu=0.0, omega=2e-7, alpha_garch=0.08, beta_garch=0.90)
    a_kw.update(dataset_a_kwargs or {})
    b_kw = dict(
        mu=0.0, sigma_base=0.003, k_cascade=6, p1=0.25, decay=0.45, m_low=0.5, m_high=1.5,
        hawkes_lambda0=0.005, hawkes_alpha=0.15, hawkes_beta=0.35, hawkes_ratio_cap=5.0, pareto_xm=0.0025, pareto_alpha=2.6,
    )
    b_kw.update(dataset_b_kwargs or {})

    # --- estado GARCH (proceso "calma", persiste siempre en 2do plano) ---
    sigma2 = a_kw["omega"] / max(1e-9, (1 - a_kw["alpha_garch"] - a_kw["beta_garch"]))
    prev_r2 = sigma2

    # --- estado cascada + Hawkes (proceso "crítico", persiste siempre en 2do plano) ---
    switch_probs = np.array([min(0.5, b_kw["p1"] * (b_kw["decay"] ** i)) for i in range(b_kw["k_cascade"])])
    multipliers = rng.choice([b_kw["m_low"], b_kw["m_high"]], size=b_kw["k_cascade"])
    hawkes_intensity_excess = 0.0

    returns = np.empty(n)
    intrabar_vol = np.empty(n)
    volume = np.empty(n)
    regime = np.empty(n, dtype=object)

    state = "calm"
    for i in range(n):
        # transición de régimen (Markov de 2 estados)
        if state == "calm":
            if rng.random() < p_enter_critical:
                state = "critical"
        else:
            if rng.random() < p_exit_critical:
                state = "calm"
        regime[i] = state

        # --- avanzar SIEMPRE ambos procesos subyacentes ---
        sigma2 = a_kw["omega"] + a_kw["alpha_garch"] * prev_r2 + a_kw["beta_garch"] * sigma2
        sigma_a = np.sqrt(sigma2)
        eps_a = rng.normal()
        r_a = a_kw["mu"] + sigma_a * eps_a
        prev_r2 = r_a * r_a

        _msm_step(multipliers, switch_probs, b_kw["m_low"], b_kw["m_high"], rng)
        sigma_b = b_kw["sigma_base"] * np.sqrt(np.prod(multipliers))
        hawkes_intensity_excess *= np.exp(-b_kw["hawkes_beta"])
        lam = b_kw["hawkes_lambda0"] + hawkes_intensity_excess
        shock = 0.0
        if rng.random() < min(0.98, lam):
            u = rng.random()
            magnitude = _pareto_sample(u, b_kw["pareto_xm"], b_kw["pareto_alpha"])
            magnitude = min(magnitude, b_kw["pareto_xm"] * 40)
            sign = 1.0 if rng.random() < 0.5 else -1.0
            shock = sign * magnitude
            hawkes_intensity_excess += b_kw["hawkes_alpha"] * min(magnitude / b_kw["pareto_xm"], b_kw["hawkes_ratio_cap"])
        eps_b = rng.normal()
        r_b = b_kw["mu"] + sigma_b * eps_b + shock

        # --- realizar el retorno del proceso activo ---
        if state == "calm":
            returns[i] = r_a
            intrabar_vol[i] = sigma_a
            vshock = False
        else:
            returns[i] = r_b
            intrabar_vol[i] = sigma_b
            vshock = shock != 0.0

        vol_base = rng.lognormal(mean=9.0, sigma=0.4)
        extra = (6.0 if vshock else 0.0) + (2.0 if state == "critical" else 0.0)
        volume[i] = max(1.0, vol_base * (1 + extra + 3.0 * abs(returns[i]) / max(intrabar_vol[i], 1e-9) * 0.05))

    df = _bars_from_returns(ts, returns, intrabar_vol, volume, start_price, gap_std=0.002, rng=rng)
    df["regime"] = regime
    return df
