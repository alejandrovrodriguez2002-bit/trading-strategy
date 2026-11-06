import numpy as np
import pandas as pd

from src.market_regime import RegimeConfig, _apply_hysteresis, compute_regime


def _df_from_close(values):
    idx = pd.date_range("2026-01-02 09:30", periods=len(values), freq="5min", tz="America/New_York")
    return pd.DataFrame({"close": values}, index=idx)


def test_regime_values_are_always_in_valid_set():
    rng = np.random.default_rng(0)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.001, 600)))
    df = _df_from_close(close)
    out = compute_regime(df)
    assert set(out["regime"].unique()).issubset({-1, 0, 1})
    assert len(out) == len(df)


def test_regime_is_neutral_during_warmup():
    rng = np.random.default_rng(1)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.001, 50)))  # menos barras que cualquier longitud mínima
    df = _df_from_close(close)
    cfg = RegimeConfig(hurst_length=100, fractal_length=60, entropy_length=100, er_length=30,
                        gex_short=20, gex_long=250)
    out = compute_regime(df, cfg)
    assert (out["regime"] == 0).all()


def test_strong_monotonic_trend_favors_structured_votes():
    """Una serie que sube en línea recta (sin ruido) debe dar eficiencia de
    Kaufman muy alta (~1, voto ESTRUCTURADO) y Hurst alto -- aunque el
    régimen final también depende de GEX/entropía/fractal, los votos
    direccionales clave deben apuntar a ESTRUCTURADO."""
    n = 400
    close = 100 + np.arange(n) * 0.05  # rampa lineal perfecta
    df = _df_from_close(close)
    out = compute_regime(df)
    tail = out.iloc[-50:]
    assert (tail["er_sig"] == 1).all()  # eficiencia ~1 en una rampa perfecta -> ESTRUCTURADO
    assert (tail["hurst_sig"] >= 0).all()  # nunca debería votar REVERSIÓN en una tendencia perfecta


def test_efficiency_ratio_is_near_one_for_perfect_trend_and_near_zero_for_round_trip():
    n = 100
    trend = _df_from_close(100 + np.arange(n) * 0.1)
    out_trend = compute_regime(trend)
    assert out_trend["efficiency"].iloc[-1] > 0.9

    # sube y baja de vuelta casi al mismo precio dentro de la ventana de ER
    # (30 velas por defecto) -> cambio neto ~0, mucho camino recorrido -> ER ~0
    up = 100 + np.arange(16)  # 0..15
    down = up[-1] - np.arange(1, 16)  # 16..30, vuelve a 100
    round_trip = _df_from_close(np.concatenate([up, down]))
    out_rt = compute_regime(round_trip)
    assert out_rt["efficiency"].iloc[-1] < 0.1


def test_apply_hysteresis_requires_min_bars_of_persistence():
    # el candidato cambia a 1 pero solo dura 2 barras (min_bars=3) -> no debe cambiar el régimen
    candidate = np.array([0, 0, 1, 1, 0, 0, 0])
    regime = _apply_hysteresis(candidate, min_bars=3)
    assert (regime == 0).all()


def test_apply_hysteresis_changes_regime_after_min_bars_of_persistence():
    candidate = np.array([0, 0, 1, 1, 1, 1, 1])
    regime = _apply_hysteresis(candidate, min_bars=3)
    # cambia a partir de la 3ra vela consecutiva en 1 (índice 4, 0-based)
    assert list(regime) == [0, 0, 0, 0, 1, 1, 1]


def test_apply_hysteresis_does_not_reset_on_a_different_candidate_once_back_to_current_regime():
    # patrón: ya en régimen 0; candidato titila 1,1,-1,1,1,1 -> el conteo de 1 se
    # reinicia cuando aparece -1 en medio (es un candidato distinto), pero al volver
    # a aparecer 1 se vuelve a contar desde ahí
    candidate = np.array([0, 1, 1, -1, 1, 1, 1])
    regime = _apply_hysteresis(candidate, min_bars=3)
    assert list(regime) == [0, 0, 0, 0, 0, 0, 1]
