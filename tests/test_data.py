import io

import pandas as pd

from src.data import _fix_yahoo_zero_open_volume, load_csv


def test_load_csv_dedupes_close_and_adj_close():
    """Regresión: CSVs de Yahoo traen 'Close' Y 'Adj Close' a la vez, ambas
    se mapean a 'close' -> antes producía una columna 'close' duplicada que
    rompía cualquier operación aritmética entre columnas (ver src/cvd.py)."""
    csv_text = (
        "Datetime,Open,High,Low,Close,Adj Close,Volume\n"
        "2026-01-02 09:30:00-05:00,100,101,99,100.5,100.5,1000\n"
        "2026-01-02 09:35:00-05:00,100.5,102,100,101.5,101.5,2000\n"
    )
    df = load_csv(io.StringIO(csv_text))
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert not df.columns.duplicated().any()
    assert df["close"].tolist() == [100.5, 101.5]


def test_fix_yahoo_zero_open_volume_replaces_first_bar_of_day():
    idx = pd.date_range("2026-01-02 09:30", periods=4, freq="5min", tz="America/New_York").append(
        pd.date_range("2026-01-05 09:30", periods=4, freq="5min", tz="America/New_York")
    )
    df = pd.DataFrame(
        {
            "open": [1] * 8,
            "high": [1] * 8,
            "low": [1] * 8,
            "close": [1] * 8,
            "volume": [0, 100, 200, 300, 0, 500, 600, 700],
        },
        index=idx,
    )
    out = _fix_yahoo_zero_open_volume(df.copy())
    # el volume==0 de la primera vela de cada dia se reemplaza por el de la siguiente
    assert out["volume"].iloc[0] == 100
    assert out["volume"].iloc[4] == 500
    # el resto de las velas no se toca
    assert list(out["volume"].iloc[1:4]) == [100, 200, 300]
    assert list(out["volume"].iloc[5:8]) == [500, 600, 700]


def test_fix_yahoo_zero_open_volume_leaves_non_open_zeros_alone():
    idx = pd.date_range("2026-01-02 09:30", periods=3, freq="5min", tz="America/New_York")
    df = pd.DataFrame(
        {"open": [1] * 3, "high": [1] * 3, "low": [1] * 3, "close": [1] * 3, "volume": [100, 0, 300]},
        index=idx,
    )
    out = _fix_yahoo_zero_open_volume(df.copy())
    assert list(out["volume"]) == [100, 0, 300]
