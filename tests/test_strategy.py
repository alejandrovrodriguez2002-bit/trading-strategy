import pandas as pd

from src.config import Config
from src.cvd import add_cvd
from src.strategy import _volume_surge_ok, generate_trades


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


def test_volume_surge_ok_true_with_clear_spike():
    cfg = Config(volume_filter_enabled=True, volume_lookback_bars=10, volume_multiplier=1.5)
    baseline = [1000] * 10
    or_window = [5000, 5000, 5000]  # 5x la línea base
    df = _flat_df(baseline + or_window)
    start_pos = 10
    or_end_pos = 13
    assert _volume_surge_ok(df, start_pos, or_end_pos, cfg) is True


def test_volume_surge_ok_false_without_spike():
    cfg = Config(volume_filter_enabled=True, volume_lookback_bars=10, volume_multiplier=1.5)
    baseline = [1000] * 10
    or_window = [1000, 1100, 900]  # sin repunte real
    df = _flat_df(baseline + or_window)
    assert _volume_surge_ok(df, 10, 13, cfg) is False


def test_volume_surge_ok_disabled_always_true():
    cfg = Config(volume_filter_enabled=False, volume_lookback_bars=10, volume_multiplier=1.5)
    df = _flat_df([1000] * 13)
    assert _volume_surge_ok(df, 10, 13, cfg) is True


def test_volume_surge_ok_no_baseline_history_passes():
    cfg = Config(volume_filter_enabled=True, volume_lookback_bars=20, volume_multiplier=1.5)
    df = _flat_df([1000] * 5)  # no hay 20 velas previas -> no se puede evaluar, se deja pasar
    assert _volume_surge_ok(df, 0, 3, cfg) is True


def test_filter_never_generates_more_trades_than_without_it():
    """El filtro de volumen solo puede DESCARTAR días, nunca agregar trades
    nuevos -> con el filtro activo, el número de trades debe ser <= sin él."""
    from src.synthetic_datasets import generate_dataset_a

    df = generate_dataset_a(months_back=2)
    df = add_cvd(df, reset_daily=True)

    cfg_on = Config(volume_filter_enabled=True, volume_lookback_bars=20, volume_multiplier=1.5)
    cfg_off = Config(volume_filter_enabled=False)

    trades_on = generate_trades(df, cfg_on)
    trades_off = generate_trades(df, cfg_off)

    assert len(trades_on) <= len(trades_off)
