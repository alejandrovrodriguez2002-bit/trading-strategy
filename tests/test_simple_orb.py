import pandas as pd

from src.simple_orb import SimpleORBConfig, generate_trades_simple, run_backtest_simple


def _bar(o, h, l, c, v):
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}


def _make_df(rows, start="2026-01-02 09:30", freq="5min", tz="America/New_York"):
    idx = pd.date_range(start, periods=len(rows), freq=freq, tz=tz)
    return pd.DataFrame(rows, index=idx)


def test_long_breakout_fills_at_or_high_and_hits_fixed_r_take_profit():
    # OR (2 velas de 5min = primeros 10 min): high=101, low=99
    rows = [
        _bar(100, 101, 99, 100.5, 1000),
        _bar(100.5, 100.8, 99.5, 100, 1000),
        # rompe el high del OR
        _bar(100, 101.5, 100, 101.2, 1000),
        # sube hasta el TP (SL=or_low=99, riesgo=101-99=2, TP=2R -> 101+4=105)
        _bar(101.2, 105.5, 101, 105, 1000),
        _bar(105, 105.2, 104.8, 105, 1000),
    ]
    df = _make_df(rows)
    cfg = SimpleORBConfig(
        or_minutes=10, volume_filter_enabled=False, sl_mode="or_opposite",
        tp_r_multiple=2.0, sl_buffer_pct=0.0, slippage_bps=0.0, session_only=False,
    )
    trades = generate_trades_simple(df, cfg)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["direction"] == "long"
    assert t["entry_price"] == 101.0  # relleno en el nivel del OR (sin gap)
    assert t["sl"] == 99.0
    assert t["tp"] == 105.0
    assert t["exit_reason"] == "TP"


def test_short_breakout_stopped_out_at_or_opposite():
    rows = [
        _bar(100, 101, 99, 99.5, 1000),
        _bar(99.5, 100, 99.2, 99.5, 1000),
        # rompe el low del OR -> short
        _bar(99.5, 99.6, 98.5, 98.7, 1000),
        # sube y toca el SL (or_high=101)
        _bar(98.7, 101.5, 98.6, 101, 1000),
    ]
    df = _make_df(rows)
    cfg = SimpleORBConfig(
        or_minutes=10, volume_filter_enabled=False, sl_mode="or_opposite",
        tp_r_multiple=2.0, sl_buffer_pct=0.0, slippage_bps=0.0, session_only=False,
    )
    trades = generate_trades_simple(df, cfg)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["direction"] == "short"
    assert t["entry_price"] == 99.0
    assert t["sl"] == 101.0
    assert t["exit_reason"] == "SL"
    assert t["pnl"] < 0


def test_gap_beyond_or_level_fills_at_open_not_at_stale_level():
    rows = [
        _bar(100, 101, 99, 100.5, 1000),
        _bar(100.5, 100.8, 99.5, 100, 1000),
        # gap: abre ya por encima del OR high (101) -> se rellena en el open, no en 101
        _bar(102, 102.5, 101.8, 102.2, 1000),
        _bar(102.2, 102.3, 102.1, 102.2, 1000),
    ]
    df = _make_df(rows)
    cfg = SimpleORBConfig(
        or_minutes=10, volume_filter_enabled=False, sl_mode="or_opposite",
        tp_r_multiple=2.0, sl_buffer_pct=0.0, slippage_bps=0.0, session_only=False,
    )
    trades = generate_trades_simple(df, cfg)
    assert len(trades) == 1
    assert trades.iloc[0]["entry_price"] == 102.0


def test_trend_filter_rejects_long_after_bearish_prior_day():
    prior_day = [
        _bar(100, 100.5, 95, 96, 1000),  # día anterior bajista (close < open)
    ]
    today = [
        _bar(96, 97, 95.5, 96.5, 1000),
        _bar(96.5, 96.8, 96.2, 96.5, 1000),
        # rompe el high -> sesgo long, pero el día anterior fue bajista -> debe rechazarse
        _bar(96.5, 98, 96.5, 97.8, 1000),
        _bar(97.8, 99, 97.5, 98.5, 1000),
    ]
    idx1 = pd.date_range("2026-01-02 09:30", periods=1, freq="5min", tz="America/New_York")
    idx2 = pd.date_range("2026-01-05 09:30", periods=4, freq="5min", tz="America/New_York")
    df = pd.concat([pd.DataFrame(prior_day, index=idx1), pd.DataFrame(today, index=idx2)])

    cfg = SimpleORBConfig(
        or_minutes=10, volume_filter_enabled=False, sl_mode="or_opposite",
        trend_filter_enabled=True, sl_buffer_pct=0.0, slippage_bps=0.0, session_only=False,
    )
    trades = generate_trades_simple(df, cfg)
    assert len(trades) == 0


def test_liquidity_sl_mode_falls_back_to_farther_swing_without_liquidity_on_nearest():
    """Igual patrón que tests/test_liquidity_filter.py: valida
    _compute_sl_tp_simple directamente (no el flujo de rompimiento
    completo), que es lo que decide el SL cuando sl_mode="liquidity"."""
    from src.simple_orb import _compute_sl_tp_simple

    idx = pd.date_range("2026-01-02 09:30", periods=30, freq="5min", tz="America/New_York")
    high = [100.0] * 30
    low = [99.0] * 30
    close = [99.5] * 30
    volume = [1000] * 30

    # swing high cercano (bajo volumen) a 105 -- no debe calificar
    high[10], volume[10] = 105.0, 1000
    # swing high más lejano (alto volumen) a 110 -- pool de liquidez real
    high[5], volume[5] = 110.0, 10000

    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": volume}, index=idx)

    cfg = SimpleORBConfig(
        sl_mode="liquidity", liquidity_filter_enabled=True, liquidity_lookback_bars=3,
        liquidity_multiplier=1.5, swing_fractal_window=2, swing_lookback_days=5, sl_buffer_pct=0.0,
    )
    sl, tp, reason = _compute_sl_tp_simple(df, entry_pos=20, entry_price=100.0, direction="short",
                                            sl_anchor_price=101.0, cfg=cfg)
    assert sl is not None
    assert sl == 110.0  # ancla en el swing con liquidez real, no en el de 105 (más cercano pero sin volumen)


def test_fade_mode_shorts_a_high_breakout_with_sl_above_the_wick():
    rows = [
        _bar(100, 101, 99, 100.5, 1000),
        _bar(100.5, 100.8, 99.5, 100, 1000),
        # rompe el high del OR con una mecha hasta 103 pero cierra más abajo (posible falso rompimiento)
        _bar(100, 103, 100, 100.5, 1000),
        # revierte hacia abajo -> favorable para el fade (short)
        _bar(100.5, 100.6, 97, 97.5, 1000),
    ]
    df = _make_df(rows)
    cfg = SimpleORBConfig(
        or_minutes=10, volume_filter_enabled=False, sl_mode="or_opposite",
        direction_mode="fade", tp_r_multiple=1.0, sl_buffer_pct=0.03,
        slippage_bps=0.0, session_only=False,
    )
    trades = generate_trades_simple(df, cfg)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["direction"] == "short"  # se fadea el rompimiento del high -> short
    assert t["entry_price"] == 101.0  # relleno en el nivel del OR roto
    assert t["sl"] > 103.0  # ancla en la mecha real (103), no en el nivel del OR (101)


def test_session_poc_finds_bin_with_dominant_volume():
    from src.simple_orb import _session_poc

    idx = pd.date_range("2026-01-02 09:30", periods=5, freq="5min", tz="America/New_York")
    rows = [
        _bar(100, 101, 99, 100, 10),
        _bar(100, 105, 99, 104, 10),
        _bar(104, 104.5, 95, 96, 100000),  # domina el volumen, precio típico ~98.5
        _bar(96, 97, 95.5, 96.5, 10),
        _bar(96.5, 97, 96, 96.8, 10),
    ]
    df = pd.DataFrame(rows, index=idx)
    poc = _session_poc(df, n_bins=30)
    assert poc is not None
    assert 97.5 < poc < 99.5  # cerca del precio típico de la vela dominante ((104.5+95+96)/3 = 98.5)


def test_prev_session_range_source_fade_targets_opposite_extreme():
    """range_source="prev_session": el rompimiento se mide contra el
    high/low de TODA la sesión anterior (PDH/PDL), y en modo fade con
    tp_mode="opposite_extreme" el objetivo es el lado NO roto de ese rango
    (el low del día anterior, si se barrió el high)."""
    day1 = [
        _bar(100, 101, 99, 100, 1000),
        _bar(100, 105, 99, 104, 1000),     # PDH = 105
        _bar(104, 104.5, 95, 96, 1000),    # PDL = 95
        _bar(96, 97, 95.5, 96.5, 1000),
        _bar(96.5, 97, 96, 96.8, 1000),
    ]
    day2 = [
        _bar(97, 98, 96.5, 97.5, 1000),
        _bar(97.5, 98, 97, 97.8, 1000),
        _bar(97.8, 106, 99, 105.5, 1000),   # barre el PDH (105) -> raw_direction long -> fade a short
        _bar(105.5, 105.8, 95, 95.2, 1000),  # revierte hasta el PDL (95) -> TP del fade
    ]
    idx1 = pd.date_range("2026-01-02 09:30", periods=len(day1), freq="5min", tz="America/New_York")
    idx2 = pd.date_range("2026-01-05 09:30", periods=len(day2), freq="5min", tz="America/New_York")
    df = pd.concat([pd.DataFrame(day1, index=idx1), pd.DataFrame(day2, index=idx2)])

    cfg = SimpleORBConfig(
        range_source="prev_session", direction_mode="fade", tp_mode="opposite_extreme",
        volume_filter_enabled=False, sl_buffer_pct=0.03, slippage_bps=0.0, session_only=False,
    )
    trades = generate_trades_simple(df, cfg)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["direction"] == "short"        # se barrió el PDH -> fade en short
    assert t["or_high"] == 105.0 and t["or_low"] == 95.0  # PDH/PDL del día anterior
    assert t["entry_price"] == 105.0        # relleno en el nivel del PDH
    assert t["tp"] == 95.0                  # objetivo: el lado opuesto (PDL), no un múltiplo de R
    assert t["exit_reason"] == "TP"


def test_poc_tp_mode_targets_previous_session_point_of_control():
    from src.simple_orb import _session_poc

    day1 = [
        _bar(100, 101, 99, 100, 10),
        _bar(100, 105, 99, 104, 10),        # PDH = 105
        _bar(104, 104.5, 95, 96, 100000),   # domina el volumen -> ancla el POC ~98.5
        _bar(96, 97, 95.5, 96.5, 10),
        _bar(96.5, 97, 96, 96.8, 10),       # PDL = 95
    ]
    day2 = [
        _bar(97, 98, 96.5, 97.5, 1000),
        _bar(97.5, 98, 97, 97.8, 1000),
        _bar(97.8, 106, 99, 105.5, 1000),   # barre el PDH -> fade a short
        _bar(105.5, 105.8, 96, 96.5, 1000),  # baja lo suficiente para tocar el POC como TP
    ]
    idx1 = pd.date_range("2026-01-02 09:30", periods=len(day1), freq="5min", tz="America/New_York")
    idx2 = pd.date_range("2026-01-05 09:30", periods=len(day2), freq="5min", tz="America/New_York")
    day1_df = pd.DataFrame(day1, index=idx1)
    df = pd.concat([day1_df, pd.DataFrame(day2, index=idx2)])

    expected_poc = _session_poc(day1_df, n_bins=30)

    cfg = SimpleORBConfig(
        range_source="prev_session", direction_mode="fade", tp_mode="poc",
        volume_filter_enabled=False, sl_buffer_pct=0.03, slippage_bps=0.0, session_only=False,
    )
    trades = generate_trades_simple(df, cfg)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["direction"] == "short"
    assert t["tp"] == expected_poc
    assert t["exit_reason"] == "TP"


def test_run_backtest_simple_builds_equity_curve():
    rows = [
        _bar(100, 101, 99, 100.5, 1000),
        _bar(100.5, 100.8, 99.5, 100, 1000),
        _bar(100, 101.5, 100, 101.2, 1000),
        _bar(101.2, 105.5, 101, 105, 1000),
        _bar(105, 105.2, 104.8, 105, 1000),
    ]
    df = _make_df(rows)
    cfg = SimpleORBConfig(
        or_minutes=10, volume_filter_enabled=False, sl_mode="or_opposite",
        tp_r_multiple=2.0, sl_buffer_pct=0.0, slippage_bps=0.0, session_only=False,
    )
    trades, equity_curve = run_backtest_simple(df, cfg)
    assert len(trades) == 1
    assert equity_curve.iloc[-1] > equity_curve.iloc[0]  # ganó el TP
