import numpy as np
import pandas as pd

from src.metrics import cagr, max_drawdown, sharpe_ratio, sortino_ratio


def test_max_drawdown():
    eq = pd.Series([100, 120, 90, 110], index=pd.date_range("2026-01-01", periods=4))
    dd = max_drawdown(eq)
    assert np.isclose(dd, (90 - 120) / 120)


def test_sortino_zero_when_no_downside():
    eq = pd.Series([100, 101, 102, 103, 104], index=pd.date_range("2026-01-01", periods=5))
    s = sortino_ratio(eq)
    assert s == 0.0  # sin retornos negativos, downside_dev=0 -> definido como 0 (evita división por 0)


def test_sharpe_positive_for_uptrend():
    idx = pd.date_range("2026-01-01", periods=30)
    eq = pd.Series(100 * (1.001 ** np.arange(30)), index=idx)
    assert sharpe_ratio(eq) > 0


def test_cagr_reasonable():
    idx = pd.date_range("2026-01-01", periods=366)
    eq = pd.Series(np.linspace(100, 200, 366), index=idx)
    c = cagr(eq)
    assert 0.9 < c < 1.1  # ~100% en ~1 año
