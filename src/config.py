"""Carga de configuración de la estrategia desde YAML."""
from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Optional

import yaml


@dataclasses.dataclass
class Config:
    ticker: str = "QQQ"
    timezone: str = "America/New_York"

    session_open: str = "09:30"
    session_close: str = "16:00"
    session_only: bool = True

    or_minutes: int = 15

    volume_filter_enabled: bool = True
    volume_lookback_bars: int = 20
    volume_multiplier: float = 1.5

    poc_filter_enabled: bool = True
    poc_bin_pct: float = 0.0005
    poc_std_low_k: float = 1.0
    poc_std_high_k: float = 2.0

    pivot_lookback: int = 1
    max_bars_after_breakout: Optional[int] = None
    invalidate_on_full_retrace: bool = True

    starting_equity: float = 10_000.0
    risk_per_trade_pct: float = 1.0
    sl_buffer_pct: float = 0.03
    max_trades_per_day: int = 1
    slippage_bps: float = 1.0
    commission_per_trade: float = 0.0

    swing_fractal_window: int = 3
    swing_lookback_days: int = 5

    interval: str = "5m"
    months_back: int = 6

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Config":
        with open(path, "r") as f:
            raw = yaml.safe_load(f)

        return cls(
            ticker=raw["instrument"]["ticker"],
            timezone=raw["instrument"]["timezone"],
            session_open=raw["session"]["open"],
            session_close=raw["session"]["close"],
            session_only=raw["session"]["session_only"],
            or_minutes=raw["opening_range"]["minutes"],
            volume_filter_enabled=raw.get("volume_filter", {}).get("enabled", True),
            volume_lookback_bars=raw.get("volume_filter", {}).get("lookback_bars", 20),
            volume_multiplier=raw.get("volume_filter", {}).get("multiplier", 1.5),
            poc_filter_enabled=raw.get("poc_filter", {}).get("enabled", True),
            poc_bin_pct=raw.get("poc_filter", {}).get("bin_pct", 0.0005),
            poc_std_low_k=raw.get("poc_filter", {}).get("std_low_k", 1.0),
            poc_std_high_k=raw.get("poc_filter", {}).get("std_high_k", 2.0),
            pivot_lookback=raw["absorption"]["pivot_lookback"],
            max_bars_after_breakout=raw["absorption"]["max_bars_after_breakout"],
            invalidate_on_full_retrace=raw["absorption"]["invalidate_on_full_retrace"],
            starting_equity=raw["risk"]["starting_equity"],
            risk_per_trade_pct=raw["risk"]["risk_per_trade_pct"],
            sl_buffer_pct=raw["risk"]["sl_buffer_pct"],
            max_trades_per_day=raw["risk"]["max_trades_per_day"],
            slippage_bps=raw["risk"]["slippage_bps"],
            commission_per_trade=raw["risk"]["commission_per_trade"],
            swing_fractal_window=raw["swings"]["fractal_window"],
            swing_lookback_days=raw["swings"]["lookback_days"],
            interval=raw["data"]["interval"],
            months_back=raw["data"]["months_back"],
        )
