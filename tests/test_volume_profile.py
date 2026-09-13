import pandas as pd

from src.volume_profile import get_prior_week_poc, weekly_poc


def _weekly_df():
    idx = pd.date_range("2026-01-05 09:30", periods=10, freq="1D", tz="America/New_York")  # 2 semanas (lun-vie x2)
    close = [100.0] * 10
    volume = [1000] * 10
    volume[2] = 100_000  # pico de volumen claro en la 1ra semana (miércoles)
    volume[7] = 50_000   # pico distinto en la 2da semana
    close[2] = 105.0
    close[7] = 95.0
    high = [c + 0.5 for c in close]
    low = [c - 0.5 for c in close]
    return pd.DataFrame({"high": high, "low": low, "close": close, "volume": volume}, index=idx)


def test_weekly_poc_finds_high_volume_price():
    df = _weekly_df()
    pocs = weekly_poc(df, bin_pct=0.01)
    prices = sorted(pocs.values())
    assert any(abs(p - 105.0) < 1.0 for p in prices)
    assert any(abs(p - 95.0) < 1.0 for p in prices)


def test_get_prior_week_poc_uses_previous_week_only():
    df = _weekly_df()
    pocs = weekly_poc(df, bin_pct=0.01)

    # una fecha dentro de la 2da semana debe usar el POC de la 1ra semana (~105), no el suyo propio (~95)
    poc = get_prior_week_poc(pocs, df.index[8])
    assert abs(poc - 105.0) < 1.0


def test_get_prior_week_poc_nan_for_first_week():
    df = _weekly_df()
    pocs = weekly_poc(df, bin_pct=0.01)
    poc = get_prior_week_poc(pocs, df.index[0])
    assert poc != poc  # nan
