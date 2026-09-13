import pandas as pd

from src.config import Config
from src.strategy import _in_valid_sd_band


def test_in_valid_sd_band_rejects_too_close_to_mean():
    stats_by_week = {(2026, 1): {"poc": 100.0, "mean": 100.0, "std": 2.0}}
    cfg = Config(poc_filter_enabled=True, poc_std_low_k=1.0, poc_std_high_k=2.0)
    # semana ISO 2 -> semana anterior es la (2026, 1)
    ts = pd.Timestamp("2026-01-05", tz="America/New_York")  # martes de la semana ISO 2026-2
    # distancia = 1.0 -> 0.5 sigma, por debajo del mínimo (1 sigma) -> rechazado
    assert _in_valid_sd_band(101.0, ts, stats_by_week, cfg) is False


def test_in_valid_sd_band_rejects_too_far_from_mean():
    stats_by_week = {(2026, 1): {"poc": 100.0, "mean": 100.0, "std": 2.0}}
    cfg = Config(poc_filter_enabled=True, poc_std_low_k=1.0, poc_std_high_k=2.0)
    ts = pd.Timestamp("2026-01-05", tz="America/New_York")
    # distancia = 5.0 -> 2.5 sigma, por encima del máximo (2 sigma) -> rechazado
    assert _in_valid_sd_band(105.0, ts, stats_by_week, cfg) is False


def test_in_valid_sd_band_accepts_between_1_and_2_sigma():
    stats_by_week = {(2026, 1): {"poc": 100.0, "mean": 100.0, "std": 2.0}}
    cfg = Config(poc_filter_enabled=True, poc_std_low_k=1.0, poc_std_high_k=2.0)
    ts = pd.Timestamp("2026-01-05", tz="America/New_York")
    # distancia = 3.0 -> 1.5 sigma, dentro de [1, 2] -> aceptado
    assert _in_valid_sd_band(103.0, ts, stats_by_week, cfg) is True


def test_in_valid_sd_band_passes_when_disabled():
    cfg = Config(poc_filter_enabled=False)
    ts = pd.Timestamp("2026-01-05", tz="America/New_York")
    assert _in_valid_sd_band(999.0, ts, {}, cfg) is True


def test_in_valid_sd_band_passes_without_prior_week():
    stats_by_week = {}  # sin semana anterior con datos
    cfg = Config(poc_filter_enabled=True)
    ts = pd.Timestamp("2026-01-05", tz="America/New_York")
    assert _in_valid_sd_band(100.0, ts, stats_by_week, cfg) is True
