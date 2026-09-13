"""Tests de las funciones puras de scripts/fetch_databento_candles.py
(la llamada real a la API de Databento no se puede probar aquí — sin red)."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fetch_databento_candles import normalize, resample_ohlcv, restrict_to_regular_session  # noqa: E402


def _fake_databento_response(n=15, start="2026-01-02 09:30", freq="1min"):
    """Simula lo que devolvería store.to_df(tz='America/New_York') para
    schema='ohlcv-1m': DatetimeIndex (ts_event) + columnas open/high/low/
    close/volume/symbol en minúscula."""
    idx = pd.date_range(start, periods=n, freq=freq, tz="America/New_York")
    df = pd.DataFrame(
        {
            "rtype": [32] * n,
            "open": range(100, 100 + n),
            "high": range(101, 101 + n),
            "low": range(99, 99 + n),
            "close": range(100, 100 + n),
            "volume": [1000] * n,
            "symbol": ["QQQ"] * n,
        },
        index=idx,
    )
    df.index.name = "ts_event"
    return df


def test_normalize_renames_and_keeps_symbol():
    raw = _fake_databento_response()
    out = normalize(raw)
    assert list(out.columns) == ["Open", "High", "Low", "Close", "Volume", "symbol"]
    assert out.index.name == "Datetime"
    assert isinstance(out.index, pd.DatetimeIndex)


def test_normalize_raises_if_missing_columns():
    raw = _fake_databento_response().drop(columns=["close"])
    with pytest.raises(ValueError, match="Faltan columnas"):
        normalize(raw)


def test_normalize_raises_if_not_datetime_index():
    raw = _fake_databento_response().reset_index(drop=True)
    with pytest.raises(ValueError, match="DatetimeIndex"):
        normalize(raw)


def test_restrict_to_regular_session_filters_out_of_hours():
    raw = _fake_databento_response(n=5, start="2026-01-02 04:00")  # pre-market
    out = normalize(raw).drop(columns=["symbol"])
    sess = restrict_to_regular_session(out)
    assert len(sess) == 0


def test_resample_ohlcv_aggregates_correctly():
    raw = _fake_databento_response(n=15)
    out = normalize(raw).drop(columns=["symbol"])
    sess = restrict_to_regular_session(out)
    resampled = resample_ohlcv(sess, "5min")

    assert len(resampled) == 3
    first = resampled.iloc[0]
    assert first["Open"] == 100
    assert first["High"] == 105
    assert first["Low"] == 99
    assert first["Close"] == 104
    assert first["Volume"] == 5000
