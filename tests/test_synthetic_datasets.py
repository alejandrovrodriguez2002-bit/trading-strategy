import numpy as np
from scipy import stats

from src.synthetic_datasets import generate_dataset_a, generate_dataset_b, generate_dataset_c


def _basic_checks(df):
    assert not df[["open", "high", "low", "close", "volume"]].isna().any().any()
    assert (df[["open", "high", "low", "close"]] > 0).all().all()
    assert (df["high"] >= df[["open", "close"]].max(axis=1)).all()
    assert (df["low"] <= df[["open", "close"]].min(axis=1)).all()
    assert (df["volume"] > 0).all()


def test_dataset_a_shape_and_sanity():
    df = generate_dataset_a(months_back=1)
    assert len(df) > 0
    _basic_checks(df)


def test_dataset_b_shape_and_sanity():
    df = generate_dataset_b(months_back=1)
    assert len(df) > 0
    _basic_checks(df)


def test_dataset_c_shape_and_sanity():
    df = generate_dataset_c(months_back=1)
    assert len(df) > 0
    _basic_checks(df.drop(columns=["regime"]))
    assert set(df["regime"].unique()) <= {"calm", "critical"}


def test_dataset_b_has_fatter_tails_than_a():
    """Reclamo central del diseño: B (SOC/multifractal) debe tener colas
    mucho más pesadas que A (tradicional/Gaussiano-GARCH), y C (híbrido)
    debe quedar en un punto intermedio."""
    a = generate_dataset_a(months_back=3)
    b = generate_dataset_b(months_back=3)
    c = generate_dataset_c(months_back=3)

    ka = stats.kurtosis(a["close"].pct_change().dropna())
    kb = stats.kurtosis(b["close"].pct_change().dropna())
    kc = stats.kurtosis(c["close"].pct_change().dropna())

    assert kb > ka
    assert kb > kc > ka - 1  # C debe quedar entre A y B (con margen de tolerancia)


def test_dataset_c_regime_fraction_reasonable():
    df = generate_dataset_c(months_back=6)
    frac_critical = (df["regime"] == "critical").mean()
    # con p_enter=0.003 y p_exit=0.02 el estacionario teórico es ~11.5%
    assert 0.03 < frac_critical < 0.35
