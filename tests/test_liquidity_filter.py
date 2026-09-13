import pandas as pd

from src.config import Config
from src.strategy import _is_liquidity_level


def _flat_df(volumes, start="2026-01-02 09:30", freq="5min"):
    n = len(volumes)
    idx = pd.date_range(start, periods=n, freq=freq, tz="America/New_York")
    return pd.DataFrame(
        {
            "open": [100.0] * n,
            "high": [101.0] * n,
            "low": [99.0] * n,
            "close": [100.0] * n,
            "volume": volumes,
        },
        index=idx,
    )


def test_is_liquidity_level_true_with_high_volume_swing():
    cfg = Config(liquidity_filter_enabled=True, liquidity_lookback_bars=10, liquidity_multiplier=1.5)
    df = _flat_df([1000] * 10 + [5000])  # la vela del swing tiene 5x el volumen de línea base
    assert _is_liquidity_level(df, 10, cfg) is True


def test_is_liquidity_level_false_with_normal_volume_swing():
    cfg = Config(liquidity_filter_enabled=True, liquidity_lookback_bars=10, liquidity_multiplier=1.5)
    df = _flat_df([1000] * 10 + [1000])  # sin repunte de volumen -> no es un pool de liquidez real
    assert _is_liquidity_level(df, 10, cfg) is False


def test_is_liquidity_level_disabled_always_true():
    cfg = Config(liquidity_filter_enabled=False)
    df = _flat_df([1000] * 11)
    assert _is_liquidity_level(df, 10, cfg) is True


def test_is_liquidity_level_no_baseline_history_passes():
    cfg = Config(liquidity_filter_enabled=True, liquidity_lookback_bars=20)
    df = _flat_df([1000] * 5)  # no hay 20 velas previas -> no se puede evaluar, se deja pasar
    assert _is_liquidity_level(df, 0, cfg) is True


def test_short_sl_uses_next_swing_when_nearest_lacks_liquidity():
    """Si el swing high más cercano no tiene volumen alto pero uno más
    lejano sí, el SL debe anclarse en ese swing con liquidez real, no en
    el más cercano sin ella."""
    from src.strategy import _compute_sl_tp

    idx = pd.date_range("2026-01-02 09:30", periods=30, freq="5min", tz="America/New_York")
    high = [100.0] * 30
    low = [99.0] * 30
    close = [99.5] * 30
    volume = [1000] * 30

    # swing high cercano (bajo volumen) a los 105
    high[10], volume[10] = 105.0, 1000  # sin repunte -> no califica
    # swing high más lejano (alto volumen) a los 110
    high[5], volume[5] = 110.0, 10000  # con repunte -> sí califica

    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": volume}, index=idx)

    cfg = Config(
        liquidity_filter_enabled=True, liquidity_lookback_bars=3, liquidity_multiplier=1.5,
        swing_fractal_window=2, swing_lookback_days=5, sl_buffer_pct=0.0,
    )
    entry_pos = 20
    entry_price = 100.0
    sl, tp, reason = _compute_sl_tp(df, entry_pos, entry_price, "short", cfg)

    assert sl is not None
    assert sl == 110.0  # ancla en el swing de liquidez real, no en el de 105 (más cercano pero sin volumen)
