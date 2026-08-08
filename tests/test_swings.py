import pandas as pd

from src.swings import find_pivots, nearest_levels


def test_find_pivots_simple():
    highs = [1, 2, 5, 2, 1, 2, 6, 2, 1]
    lows = [h - 1 for h in highs]
    idx = pd.date_range("2026-01-02 09:30", periods=len(highs), freq="5min", tz="America/New_York")
    df = pd.DataFrame({"open": highs, "high": highs, "low": lows, "close": highs, "volume": [100] * len(highs)}, index=idx)

    pivots = find_pivots(df, window=1)
    high_pivots = [p for p in pivots if p.kind == "high"]
    prices = sorted(p.price for p in high_pivots)
    assert 5 in prices
    assert 6 in prices


def test_nearest_levels_above_below():
    from src.swings import Pivot

    pivots = [
        Pivot(0, pd.Timestamp("2026-01-02"), 10, "high"),
        Pivot(1, pd.Timestamp("2026-01-02"), 15, "high"),
        Pivot(2, pd.Timestamp("2026-01-02"), 20, "high"),
        Pivot(3, pd.Timestamp("2026-01-02"), 5, "low"),
        Pivot(4, pd.Timestamp("2026-01-02"), 2, "low"),
    ]
    above = nearest_levels(pivots, "high", reference_price=12, side="above", n=2)
    assert above == [15, 20]

    below = nearest_levels(pivots, "low", reference_price=4, side="below", n=2)
    assert below == [2]
