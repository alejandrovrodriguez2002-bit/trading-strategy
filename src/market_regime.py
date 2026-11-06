"""
Port a Python de "Market Regime v7" (Pine Script v6, subido por el
usuario) -- un indicador de régimen de mercado por consenso de 5
métricas cuantitativas, cada una votando ESTRUCTURADO (+1) / VOLÁTIL (-1)
/ NEUTRAL (0):

1. Hurst (razón de varianzas): H = 0.5*log(Var(r_k)/Var(r_1))/log(k).
   H > 0.55 -> tendencia (ESTRUCTURADO); H < 0.45 -> reversión (VOLÁTIL).
2. Dimensión fractal (estilo FRAMA/Ehlers): D = (log(N1+N2)-log(N3))/log(2).
   D < 1.35 -> suave (ESTRUCTURADO); D > 1.55 -> rugoso (VOLÁTIL).
3. Entropía de permutación (orden 3, lag 1): clasifica cada tripleta de
   precios consecutivos en 1 de 6 patrones de orden, mide la entropía de
   Shannon de la distribución de patrones en una ventana, normalizada a
   [0,1]. Entropía baja -> orden (ESTRUCTURADO); alta -> aleatorio (VOLÁTIL).
4. Eficiencia de Kaufman: ER = |cambio neto| / (suma de cambios absolutos).
   ER alto -> tendencia limpia (ESTRUCTURADO); ER bajo -> ruido (VOLÁTIL).
5. GEX proxy: -log(stdev_corta/stdev_larga) suavizado con EMA. Positivo
   (volatilidad comprimida) -> ESTRUCTURADO; negativo (expandiéndose) ->
   VOLÁTIL. Es un voto más, no obligatorio (replica el default de Pine).

Consenso: suma de los 5 votos (el de GEX con su propio peso); régimen
candidato = +1 si la suma >= umbral, -1 si <= -umbral, si no 0. Histéresis:
el régimen solo cambia si el candidato se repite N velas consecutivas
(exactamente la lógica secuencial de v7 con `pending`/`pendingCount`).

Traducción hecha leyendo el código Pine línea por línea (ver el archivo
subido) -- no se pudo correr el Pine real para validar valor por valor
contra TradingView desde este entorno (no hay runtime de Pine aquí). Se
validó con pruebas de sanidad (rangos válidos, invariantes conocidas en
series sintéticas) en tests/test_market_regime.py, no con una
comparación directa contra el indicador corriendo en vivo -- si algún
valor no coincide con lo que ves en tu gráfico, dímelo con el caso
puntual y se ajusta.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd


@dataclasses.dataclass
class RegimeConfig:
    hurst_length: int = 100
    hurst_lag: int = 10
    hurst_high: float = 0.55
    hurst_low: float = 0.45

    fractal_length: int = 60
    fractal_smooth: float = 1.35
    fractal_rough: float = 1.55

    entropy_length: int = 100
    entropy_low: float = 0.93
    entropy_high: float = 0.975

    er_length: int = 30
    er_high: float = 0.28
    er_low: float = 0.12

    gex_short: int = 20
    gex_long: int = 250
    gex_smooth: int = 5
    gex_proxy_pos: float = 0.20
    gex_proxy_neg: float = -0.10
    gex_weight: int = 1
    gex_required: bool = False

    consensus: int = 2
    min_bars: int = 3


def _sign(raw: pd.Series, hi: float, lo: float) -> pd.Series:
    sig = pd.Series(np.where(raw > hi, 1, np.where(raw < lo, -1, 0)), index=raw.index)
    sig[raw.isna()] = 0
    return sig.astype(int)


def _hurst(close: pd.Series, cfg: RegimeConfig):
    r1 = np.log(close / close.shift(1))
    rk = np.log(close / close.shift(cfg.hurst_lag))
    v1 = r1.rolling(cfg.hurst_length).var(ddof=0)
    vk = rk.rolling(cfg.hurst_length).var(ddof=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        raw = 0.5 * np.log(vk / v1) / np.log(cfg.hurst_lag)
    raw = raw.clip(0.0, 1.0)
    raw = raw.where(~((v1 <= 0) | (vk <= 0) | v1.isna() | vk.isna()))
    return raw, _sign(raw, cfg.hurst_high, cfg.hurst_low)


def _fractal(close: pd.Series, cfg: RegimeConfig):
    half = cfg.fractal_length // 2
    hi1, lo1 = close.rolling(half).max(), close.rolling(half).min()
    n1 = (hi1 - lo1) / half
    shifted = close.shift(half)
    hi2, lo2 = shifted.rolling(half).max(), shifted.rolling(half).min()
    n2 = (hi2 - lo2) / half
    hi3, lo3 = close.rolling(cfg.fractal_length).max(), close.rolling(cfg.fractal_length).min()
    n3 = (hi3 - lo3) / cfg.fractal_length

    valid = n1.notna() & n2.notna() & n3.notna()
    positive = (n1 > 0) & (n2 > 0) & (n3 > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        computed = (np.log(n1 + n2) - np.log(n3)) / np.log(2.0)
    raw = pd.Series(np.where(positive, computed, 1.5), index=close.index)
    raw = raw.clip(1.0, 2.0)
    raw = raw.where(valid)
    sig = pd.Series(np.where(raw < cfg.fractal_smooth, 1, np.where(raw > cfg.fractal_rough, -1, 0)), index=close.index)
    sig[raw.isna()] = 0
    return raw, sig.astype(int)


def _entropy(close: pd.Series, cfg: RegimeConfig):
    a, b, c = close.shift(2), close.shift(1), close
    # pat = a<b ? (b<c?0:a<c?1:2) : (a<c?3:b<c?4:5)  (traducción exacta del Pine)
    ab = a < b
    pat = np.where(
        ab,
        np.where(b < c, 0, np.where(a < c, 1, 2)),
        np.where(a < c, 3, np.where(b < c, 4, 5)),
    )
    pat = pd.Series(pat, index=close.index)
    pat[a.isna() | b.isna()] = -1  # sin datos suficientes todavía

    length = cfg.entropy_length
    counts = {k: (pat == k).astype(int).rolling(length).sum() for k in range(6)}

    def _plogp(cnt):
        q = cnt / length
        return np.where(q > 0, -q * np.log(q), 0.0)

    h = sum(_plogp(counts[k]) for k in range(6)) / np.log(6.0)
    raw = pd.Series(h, index=close.index)
    warmup = min(length + 2, len(close))
    raw.iloc[:warmup] = np.nan
    sig = pd.Series(np.where(raw < cfg.entropy_low, 1, np.where(raw > cfg.entropy_high, -1, 0)), index=close.index)
    sig[raw.isna()] = 0
    return raw, sig.astype(int)


def _efficiency_ratio(close: pd.Series, cfg: RegimeConfig):
    length = cfg.er_length
    path = close.diff().abs().rolling(length).sum()
    net = (close - close.shift(length)).abs()
    raw = pd.Series(np.where(path > 0, net / path, 0.0), index=close.index)
    raw = raw.where(path.notna())
    sig = pd.Series(np.where(raw > cfg.er_high, 1, np.where(raw < cfg.er_low, -1, 0)), index=close.index)
    sig[raw.isna()] = 0
    return raw, sig.astype(int)


def _gex_proxy(close: pd.Series, cfg: RegimeConfig):
    r1 = np.log(close / close.shift(1))
    vol_short = r1.rolling(cfg.gex_short).std(ddof=0)
    vol_long = r1.rolling(cfg.gex_long).std(ddof=0)
    vol_ratio = vol_short / vol_long
    vol_ratio_s = vol_ratio.ewm(span=cfg.gex_smooth, adjust=False).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        raw = -np.log(vol_ratio_s)
    raw = raw.where(vol_ratio_s > 0)
    sig = pd.Series(
        np.where(raw > cfg.gex_proxy_pos, 1, np.where(raw < cfg.gex_proxy_neg, -1, 0)), index=close.index
    )
    sig[raw.isna()] = 0
    return raw, sig.astype(int)


def _apply_hysteresis(candidate: np.ndarray, min_bars: int) -> np.ndarray:
    """Replica exacta del estado secuencial `regime`/`pending`/`pendingCount`
    de v7: el régimen solo cambia si el candidato se repite `min_bars`
    veces consecutivas (sin reiniciar el conteo si el candidato "titila"
    entre medio, igual que el Pine original)."""
    regime = np.zeros(len(candidate), dtype=int)
    cur_regime, pending, pending_count = 0, 0, 0
    for i, cand in enumerate(candidate):
        if cand == cur_regime:
            pending_count = 0
        else:
            if cand == pending:
                pending_count += 1
            else:
                pending = cand
                pending_count = 1
            if pending_count >= min_bars:
                cur_regime = cand
                pending_count = 0
        regime[i] = cur_regime
    return regime


def compute_regime(df: pd.DataFrame, cfg: RegimeConfig | None = None) -> pd.DataFrame:
    """Calcula el régimen por vela (columna `regime`: -1/0/1) y las 5
    métricas/votos que lo componen. `df` debe tener columna `close`."""
    cfg = cfg or RegimeConfig()
    close = df["close"]

    hurst_raw, hurst_sig = _hurst(close, cfg)
    fractal_raw, fractal_sig = _fractal(close, cfg)
    entropy_raw, entropy_sig = _entropy(close, cfg)
    er_raw, er_sig = _efficiency_ratio(close, cfg)
    gex_raw, gex_sig = _gex_proxy(close, cfg)

    net = hurst_sig + fractal_sig + entropy_sig + er_sig + gex_sig * cfg.gex_weight
    candidate = pd.Series(
        np.where(net >= cfg.consensus, 1, np.where(net <= -cfg.consensus, -1, 0)), index=close.index
    )

    if cfg.gex_required:
        candidate = candidate.where(candidate == gex_sig, 0)

    all_valid = hurst_raw.notna() & fractal_raw.notna() & entropy_raw.notna() & er_raw.notna() & gex_raw.notna()
    candidate = candidate.where(all_valid, 0)

    regime = _apply_hysteresis(candidate.values, cfg.min_bars)

    out = pd.DataFrame(
        {
            "hurst": hurst_raw, "hurst_sig": hurst_sig,
            "fractal": fractal_raw, "fractal_sig": fractal_sig,
            "entropy": entropy_raw, "entropy_sig": entropy_sig,
            "efficiency": er_raw, "er_sig": er_sig,
            "gex": gex_raw, "gex_sig": gex_sig,
            "net_votes": net,
            "regime": regime,
        },
        index=close.index,
    )
    return out
