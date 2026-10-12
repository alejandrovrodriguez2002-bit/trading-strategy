import dataclasses

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


def test_tp_mode_opposite_extreme_targets_zone_opposite_side():
    """tp_mode="opposite_extreme": tras romper el zone_high (fade a short),
    el objetivo es el zone_low -- no un múltiplo de R."""
    idx = pd.date_range("2026-01-05 19:00", periods=20, freq="5min", tz="America/New_York")
    rows = [
        _bar(100, 101, 99, 100.5, 1000),   # zona: zone_high=101
        _bar(100.5, 100.8, 99.5, 100, 1000),  # zona: zone_low=99
        _bar(100, 100.2, 99.8, 100, 1000),
        _bar(100, 100.1, 99.9, 100, 1000),
        _bar(100, 100.1, 99.9, 100, 1000),
        _bar(100, 100.1, 99.9, 100, 1000),  # fin de la zona
        _bar(100, 100.2, 99.8, 100.1, 1000),
        _bar(100.1, 103, 100, 102.5, 1000),  # rompe el zone_high -> fade a short
        _bar(102, 102.1, 98.5, 99, 1000),  # baja hasta el zone_low (99) -> TP
    ] + [_bar(99, 99.1, 98.9, 99, 1000)] * 10
    df = pd.DataFrame(rows, index=idx[: len(rows)])

    cfg = SessionZoneConfig(zone_start="19:00", zone_end="19:30", search_hours=8.5,
                             tp_mode="opposite_extreme", sl_buffer_pct=0.03, slippage_bps=0.0)
    trades = generate_trades_zone(df, cfg)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["direction"] == "short"
    assert t["tp"] == 99.0  # zone_low, no un múltiplo de R
    assert t["exit_reason"] == "TP"


def test_tp_mode_poc_targets_dominant_volume_level():
    from src.session_zone import _session_poc

    idx = pd.date_range("2026-01-05 19:00", periods=20, freq="5min", tz="America/New_York")
    rows = [
        _bar(100, 101, 99, 100.5, 10),
        _bar(100.5, 100.8, 99.5, 100, 100000),  # domina el volumen de la zona -> ancla el POC
        _bar(100, 100.2, 99.8, 100, 10),
        _bar(100, 100.1, 99.9, 100, 10),
        _bar(100, 100.1, 99.9, 100, 10),
        _bar(100, 100.1, 99.9, 100, 10),
        _bar(100, 100.2, 99.8, 100.1, 1000),
        _bar(100.1, 103, 100, 102.5, 1000),  # rompe el zone_high -> fade a short
        _bar(102, 102.1, 98.5, 99, 1000),
    ] + [_bar(99, 99.1, 98.9, 99, 1000)] * 10
    df = pd.DataFrame(rows, index=idx[: len(rows)])
    expected_poc = _session_poc(df.iloc[0:6], n_bins=30)

    cfg = SessionZoneConfig(zone_start="19:00", zone_end="19:30", search_hours=8.5,
                             tp_mode="poc", sl_buffer_pct=0.03, slippage_bps=0.0)
    trades = generate_trades_zone(df, cfg)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["direction"] == "short"
    assert t["tp"] == expected_poc


def test_liquidity_sl_mode_falls_back_to_farther_swing_without_liquidity_on_nearest():
    """Los swings de referencia para el SL deben ser HISTÓRICOS (anteriores
    a la zona), no algo que ocurra entre el fin de la zona y el
    rompimiento -- si un swing ahí superara el zone_high, ESO sería el
    rompimiento, no un swing histórico de SL."""
    n = 30
    idx = pd.date_range("2026-01-05 19:00", periods=n, freq="5min", tz="America/New_York")
    high = [100.5] * n
    low = [99.5] * n
    close = [100.0] * n
    volume = [1000] * n

    # historia previa a la zona: swing high cercano (bajo volumen) a 105 -- no debe calificar
    high[3], volume[3] = 105.0, 1000
    # historia previa a la zona: swing high más lejano (alto volumen) a 110 -- pool de liquidez real
    high[10], volume[10] = 110.0, 10000

    # zona (velas 14-15 = 20:10-20:15, zone_end=20:20): zone_high=101 (vela 14), zone_low=99 (vela 15)
    high[14] = 101.0
    low[15] = 99.0

    # rompe el zone_high en la posición 20 (por encima del zone, muy por debajo de 105/110)
    high[20], close[20] = 101.5, 101.2

    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": volume}, index=idx)

    cfg = SessionZoneConfig(
        zone_start="20:10", zone_end="20:20", search_hours=4.0,
        sl_mode="liquidity", liquidity_filter_enabled=True, liquidity_lookback_bars=3,
        liquidity_multiplier=1.5, swing_fractal_window=2, swing_lookback_days=5,
        sl_buffer_pct=0.0, slippage_bps=0.0,
    )
    trades = generate_trades_zone(df, cfg)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["direction"] == "short"
    assert t["sl"] == 110.0  # ancla en el swing con liquidez real, no en el de 105


def test_volume_subwindow_ignores_low_volume_noise_at_the_edges():
    """Con volume_subwindow_hours, el high/low de la zona debe salir de la
    sub-ventana contigua con MÁS volumen, ignorando una mecha de volumen
    bajo en otra parte de la ventana marcada (ruido de borde)."""
    n = 40
    idx = pd.date_range("2026-01-05 19:00", periods=n, freq="5min", tz="America/New_York")
    rows = [_bar(100, 100.2, 99.8, 100, 100) for _ in range(n)]
    # vela 1: mecha de ruido de BAJO volumen -- no debería definir el rango
    rows[1] = _bar(100, 110, 99.8, 100, 100)
    # velas 4-7: núcleo de ALTO volumen -- esto debe definir el rango real
    rows[4] = _bar(100, 101.0, 99.8, 100, 5000)
    rows[5] = _bar(100, 100.5, 99.0, 100, 5000)
    rows[6] = _bar(100, 100.8, 99.5, 100, 5000)
    rows[7] = _bar(100, 100.9, 99.6, 100, 5000)
    # vela 12 (fuera de la zona, zone_end=20:00 cae en la posición 12): rompe
    # el high del núcleo (101.0) pero NO el high de toda la ventana (110)
    rows[12] = _bar(100, 101.5, 100, 101.2, 1000)
    df = pd.DataFrame(rows, index=idx)

    cfg_subwindow = SessionZoneConfig(
        zone_start="19:00", zone_end="20:00", search_hours=2.0,
        volume_subwindow_hours=20 / 60, sl_buffer_pct=0.03, slippage_bps=0.0,
    )
    trades = generate_trades_zone(df, cfg_subwindow)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["zone_high"] == 101.0 and t["zone_low"] == 99.0  # del núcleo, no de toda la ventana
    assert t["direction"] == "short"

    # sin volume_subwindow_hours, el ruido de la vela 1 (110) infla el
    # zone_high y la vela 12 ya no alcanza a romperlo -> sin trade
    cfg_full_range = dataclasses.replace(cfg_subwindow, volume_subwindow_hours=None)
    trades_full = generate_trades_zone(df, cfg_full_range)
    assert len(trades_full) == 0


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
