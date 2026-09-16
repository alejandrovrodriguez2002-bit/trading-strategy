import pandas as pd

from src.session_zone import SessionZoneConfig, generate_trades_zone, run_backtest_zone


def _bar(o, h, l, c, v):
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}


def test_zone_marks_window_and_fades_breakout_within_search_horizon():
    """Zona 19:00-19:30 (como Asia): se marca el high/low de esa media
    hora, y el primer rompimiento posterior (dentro de search_hours) se
    fadea -- misma lógica que la variante OR30 validada."""
    idx = pd.date_range("2026-01-05 19:00", periods=20, freq="5min", tz="America/New_York")
    rows = [
        _bar(100, 101, 99, 100.5, 1000),   # 19:00 (zona)
        _bar(100.5, 100.8, 99.5, 100, 1000),  # 19:05 (zona) -> zone_high=101, zone_low=99
        _bar(100, 100.2, 99.8, 100, 1000),
        _bar(100, 100.1, 99.9, 100, 1000),
        _bar(100, 100.1, 99.9, 100, 1000),
        _bar(100, 100.1, 99.9, 100, 1000),  # 19:30, fin de la zona (6 velas de 5min)
        _bar(100, 100.2, 99.8, 100.1, 1000),
        _bar(100.1, 103, 100, 102.5, 1000),  # rompe el zone_high (101) -> fade a short
    ] + [_bar(102, 102.1, 99, 99.5, 1000)] + [_bar(99.5, 99.6, 99.4, 99.5, 1000)] * 10
    df = pd.DataFrame(rows, index=idx[: len(rows)])

    cfg = SessionZoneConfig(zone_start="19:00", zone_end="19:30", search_hours=8.5,
                             sl_buffer_pct=0.03, slippage_bps=0.0)
    trades = generate_trades_zone(df, cfg)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["zone_high"] == 101.0 and t["zone_low"] == 99.0
    assert t["direction"] == "short"  # se rompió el zone_high -> fade en short
    assert t["entry_price"] == 101.0


def test_zone_crossing_midnight_uses_next_day_for_zone_end():
    """Zona que cruza medianoche (ej. 23:30-00:30): zone_end debe caer al
    día SIGUIENTE, no producir una ventana invertida/vacía."""
    idx = pd.date_range("2026-01-05 23:00", periods=30, freq="5min", tz="America/New_York")
    rows = [_bar(100, 100.5, 99.5, 100, 1000) for _ in range(30)]
    # marca la zona 23:30-00:30 con un high/low distinto
    rows[6] = _bar(100, 105, 99.5, 100, 1000)  # 23:30 -> dentro de la zona, high=105
    rows[10] = _bar(100, 100.5, 95, 100, 1000)  # 23:50 -> dentro de la zona, low=95
    # después de la zona (00:30 = índice 18), rompe el high
    rows[20] = _bar(100, 106, 99.5, 105.5, 1000)
    df = pd.DataFrame(rows, index=idx)

    cfg = SessionZoneConfig(zone_start="23:30", zone_end="00:30", search_hours=4.0,
                             sl_buffer_pct=0.03, slippage_bps=0.0)
    trades = generate_trades_zone(df, cfg)
    assert len(trades) == 1
    assert trades.iloc[0]["zone_high"] == 105.0
    assert trades.iloc[0]["zone_low"] == 95.0


def test_no_trade_when_no_breakout_within_search_horizon():
    idx = pd.date_range("2026-01-05 19:00", periods=20, freq="5min", tz="America/New_York")
    rows = [_bar(100, 101, 99, 100, 1000)] * 20  # nunca rompe nada
    df = pd.DataFrame(rows, index=idx)
    cfg = SessionZoneConfig(zone_start="19:00", zone_end="19:30", search_hours=1.0, slippage_bps=0.0)
    trades = generate_trades_zone(df, cfg)
    assert len(trades) == 0


def test_run_backtest_zone_builds_equity_curve():
    idx = pd.date_range("2026-01-05 19:00", periods=20, freq="5min", tz="America/New_York")
    rows = [
        _bar(100, 101, 99, 100.5, 1000),
        _bar(100.5, 100.8, 99.5, 100, 1000),
        _bar(100, 100.2, 99.8, 100, 1000),
        _bar(100, 100.1, 99.9, 100, 1000),
        _bar(100, 100.1, 99.9, 100, 1000),
        _bar(100, 100.1, 99.9, 100, 1000),
        _bar(100, 100.2, 99.8, 100.1, 1000),
        _bar(100.1, 103, 100, 102.5, 1000),
    ] + [_bar(102, 102.1, 99, 99.5, 1000)] + [_bar(99.5, 99.6, 99.4, 99.5, 1000)] * 10
    df = pd.DataFrame(rows, index=idx[: len(rows)])
    cfg = SessionZoneConfig(zone_start="19:00", zone_end="19:30", search_hours=8.5, slippage_bps=0.0)
    trades, ec = run_backtest_zone(df, cfg)
    assert len(trades) == 1
    assert ec.iloc[-1] != ec.iloc[0]
