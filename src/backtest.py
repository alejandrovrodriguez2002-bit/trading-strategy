"""Orquesta: datos -> CVD -> estrategia -> curva de equity."""
from __future__ import annotations

import pandas as pd

from .config import Config
from .cvd import add_cvd
from .data import restrict_to_session
from .strategy import generate_trades


def run_backtest(df: pd.DataFrame, cfg: Config) -> tuple[pd.DataFrame, pd.Series]:
    if cfg.session_only:
        df = restrict_to_session(df, cfg.session_open, cfg.session_close)
    df = add_cvd(df, reset_daily=True)

    trades = generate_trades(df, cfg)

    all_dates = pd.Index(sorted(set(df.index.date)))
    equity = cfg.starting_equity
    equity_by_date = {}

    if not trades.empty:
        pnl_by_date = trades.groupby("date")["pnl"].sum().to_dict()
    else:
        pnl_by_date = {}

    # punto inicial explícito (capital antes de cualquier trade) para que
    # el capital de partida y los retornos diarios sean correctos
    if len(all_dates):
        equity_by_date[all_dates[0] - pd.Timedelta(days=1)] = equity

    for d in all_dates:
        equity += pnl_by_date.get(d, 0.0)
        equity_by_date[d] = equity

    equity_curve = pd.Series(equity_by_date, name="equity")
    equity_curve.index = pd.to_datetime(equity_curve.index)
    equity_curve = equity_curve.sort_index()

    return trades, equity_curve
