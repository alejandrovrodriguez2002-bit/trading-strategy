"""Métricas de performance del backtest."""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def _daily_returns(equity_curve: pd.Series) -> pd.Series:
    return equity_curve.pct_change().dropna()


def sharpe_ratio(equity_curve: pd.Series, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
    r = _daily_returns(equity_curve)
    if r.std(ddof=0) == 0 or len(r) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=0) * np.sqrt(periods_per_year))


def sortino_ratio(
    equity_curve: pd.Series, mar: float = 0.0, periods_per_year: int = TRADING_DAYS_PER_YEAR
) -> float:
    r = _daily_returns(equity_curve)
    if len(r) == 0:
        return 0.0
    downside = np.minimum(r - mar, 0.0)
    downside_dev = np.sqrt(np.mean(np.square(downside)))
    if downside_dev == 0:
        return 0.0
    return float((r.mean() - mar) / downside_dev * np.sqrt(periods_per_year))


def max_drawdown(equity_curve: pd.Series) -> float:
    running_max = equity_curve.cummax()
    dd = equity_curve / running_max - 1.0
    return float(dd.min()) if len(dd) else 0.0


def cagr(equity_curve: pd.Series) -> float:
    if len(equity_curve) < 2:
        return 0.0
    start_eq, end_eq = equity_curve.iloc[0], equity_curve.iloc[-1]
    days = (equity_curve.index[-1] - equity_curve.index[0]).days
    if days <= 0 or start_eq <= 0:
        return 0.0
    years = days / 365.25
    return float((end_eq / start_eq) ** (1 / years) - 1) if years > 0 else 0.0


def compute_metrics(trades: pd.DataFrame, equity_curve: pd.Series) -> dict:
    n = len(trades)
    starting_equity = equity_curve.iloc[0] if len(equity_curve) else np.nan
    ending_equity = equity_curve.iloc[-1] if len(equity_curve) else np.nan

    if n == 0:
        return {
            "num_trades": 0,
            "starting_equity": starting_equity,
            "ending_equity": ending_equity,
            "total_return_pct": 0.0,
            "cagr_pct": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": np.nan,
            "avg_win": np.nan,
            "avg_loss": np.nan,
            "expectancy_R": np.nan,
            "avg_r_multiple": np.nan,
            "max_drawdown_pct": max_drawdown(equity_curve) * 100,
            "sharpe_ratio": sharpe_ratio(equity_curve),
            "sortino_ratio": sortino_ratio(equity_curve),
            "avg_trade_duration_min": np.nan,
            "long_trades": 0,
            "short_trades": 0,
        }

    wins = trades[trades["pnl"] > 0]
    losses = trades[trades["pnl"] <= 0]

    gross_win = wins["pnl"].sum()
    gross_loss = losses["pnl"].sum()
    profit_factor = (gross_win / abs(gross_loss)) if gross_loss != 0 else np.inf

    duration = (trades["exit_time"] - trades["entry_time"]).dt.total_seconds() / 60.0

    return {
        "num_trades": n,
        "starting_equity": round(float(starting_equity), 2),
        "ending_equity": round(float(ending_equity), 2),
        "total_return_pct": round(float(ending_equity / starting_equity - 1) * 100, 2),
        "cagr_pct": round(cagr(equity_curve) * 100, 2),
        "win_rate_pct": round(float(len(wins) / n) * 100, 2),
        "profit_factor": round(float(profit_factor), 2) if np.isfinite(profit_factor) else profit_factor,
        "avg_win": round(float(wins["pnl"].mean()), 2) if len(wins) else 0.0,
        "avg_loss": round(float(losses["pnl"].mean()), 2) if len(losses) else 0.0,
        "expectancy_R": round(float(trades["r_multiple"].mean()), 3),
        "avg_r_multiple": round(float(trades["r_multiple"].mean()), 3),
        "max_drawdown_pct": round(max_drawdown(equity_curve) * 100, 2),
        "sharpe_ratio": round(sharpe_ratio(equity_curve), 3),
        "sortino_ratio": round(sortino_ratio(equity_curve), 3),
        "avg_trade_duration_min": round(float(duration.mean()), 1),
        "long_trades": int((trades["direction"] == "long").sum()),
        "short_trades": int((trades["direction"] == "short").sum()),
    }
