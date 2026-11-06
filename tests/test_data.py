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


def test_load_csv_handles_rows_with_mixed_utc_offsets_across_a_dst_change():
    """Regresión: un CSV que cruza un cambio de horario (EDT -> EST) trae
    un offset distinto por fila ("-04:00" en verano, "-05:00" en invierno)
    -- pandas ya no los deja mezclar sin utc=True (ValueError: Mixed
    timezones detected), rompiendo load_csv en cualquier archivo que
    cruce esa fecha (ej. el cambio de horario de noviembre)."""
    csv_text = (
        "Datetime,Open,High,Low,Close,Volume\n"
        "2026-10-30 09:30:00-04:00,100,101,99,100.5,1000\n"  # EDT, antes del cambio (1 nov 2026)
        "2026-11-03 09:30:00-05:00,100.5,102,100,101.5,2000\n"  # EST, después del cambio
    )
    df = load_csv(io.StringIO(csv_text))
    assert len(df) == 2
    assert str(df.index.tz) == "America/New_York"
    # ambas filas deben quedar a las 09:30 hora de NY (el cambio de horario
    # ya está resuelto correctamente, no corrido por el offset crudo)
    assert list(df.index.strftime("%H:%M")) == ["09:30", "09:30"]


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
