import pandas as pd

from src.cvd import add_bar_delta, add_cvd


def _df():
    idx = pd.date_range("2026-01-02 09:30", periods=4, freq="5min", tz="America/New_York")
    return pd.DataFrame(
        {
            "open": [100, 101, 102, 101],
            "high": [101, 102, 103, 102],
            "low": [99, 100, 101, 100],
            "close": [101, 102, 101, 100.5],  # última vela cierra cerca del low -> delta negativo
            "volume": [1000, 1000, 1000, 1000],
        },
        index=idx,
    )


def test_bar_delta_sign():
    df = add_bar_delta(_df())
    # vela 0: close (101) == high (101) -> delta debe ser positivo (todo comprador)
    assert df["delta"].iloc[0] > 0
    # vela 3: close (100.5) cerca del low (100) -> delta negativo
    assert df["delta"].iloc[3] < 0


def test_cvd_is_cumulative_and_resets_daily():
    idx1 = pd.date_range("2026-01-02 09:30", periods=2, freq="5min", tz="America/New_York")
    idx2 = pd.date_range("2026-01-05 09:30", periods=2, freq="5min", tz="America/New_York")
    df = pd.DataFrame(
        {
            "open": [100, 101, 200, 201],
            "high": [101, 102, 201, 202],
            "low": [99, 100, 199, 200],
            "close": [101, 102, 201, 202],
            "volume": [1000, 1000, 1000, 1000],
        },
        index=idx1.append(idx2),
    )
    out = add_cvd(df, reset_daily=True)
    assert out["cvd"].iloc[1] == out["delta"].iloc[0] + out["delta"].iloc[1]
    # el segundo día reinicia: no debe incluir el delta acumulado del día 1
    assert out["cvd"].iloc[2] == out["delta"].iloc[2]
