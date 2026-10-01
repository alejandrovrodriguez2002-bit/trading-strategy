"""Métricas de desempeño, alfa/beta e intervalos de confianza por bootstrap."""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

ANN = 252


def max_drawdown(r: pd.Series) -> float:
    eq = (1 + r).cumprod()
    return float((eq / eq.cummax() - 1).min())


def sortino(r: pd.Series, mar: float = 0.0) -> float:
    """Sortino anualizado: exceso medio / desviación a la baja (todos los días en el denominador)."""
    x = np.asarray(r) - mar
    dd = np.sqrt(np.mean(np.minimum(x, 0) ** 2))
    return float(np.mean(x) / dd * np.sqrt(ANN)) if dd > 0 else np.nan


def sharpe(r) -> float:
    x = np.asarray(r)
    sd = x.std(ddof=1)
    return float(x.mean() / sd * np.sqrt(ANN)) if sd > 0 else np.nan


def alpha_beta(r: pd.Series, bench: pd.Series) -> dict:
    """OLS r = a + b * bench con errores HAC (Newey-West, 5 rezagos). Alfa anualizada (x252)."""
    df = pd.concat([r.rename("s"), bench.rename("b")], axis=1).dropna()
    X = sm.add_constant(df.b)
    fit = sm.OLS(df.s, X).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    return dict(alpha_ann=float(fit.params["const"] * ANN), alpha_t=float(fit.tvalues["const"]),
                alpha_p=float(fit.pvalues["const"]), beta=float(fit.params["b"]), beta_t=float(fit.tvalues["b"]),
                r2=float(fit.rsquared), n_obs=int(len(df)), corr=float(df.s.corr(df.b)))


def block_bootstrap(r: pd.Series, n_boot: int = 5000, block: int = 5, seed: int = 7) -> dict:
    """Bootstrap estacionario por bloques: IC 90 % de Sharpe, Sortino y retorno anual."""
    rng = np.random.default_rng(seed)
    x = np.asarray(r)
    n = len(x)
    sh, so, mu = [], [], []
    for _ in range(n_boot):
        idx = np.empty(n, dtype=int)
        i = 0
        while i < n:
            start = rng.integers(n)
            L = rng.geometric(1 / block)
            seg = (start + np.arange(L)) % n
            idx[i:i + L] = seg[: n - i]
            i += L
        s = x[idx]
        sh.append(sharpe(s))
        so.append(sortino(s))
        mu.append(s.mean() * ANN)
    q = lambda a: [float(np.nanpercentile(a, 5)), float(np.nanpercentile(a, 95))]
    return dict(sharpe_ci90=q(sh), sortino_ci90=q(so), ann_ret_ci90=q(mu),
                prob_mean_le_0=float(np.mean(np.asarray(mu) <= 0)))


def summarize(r: pd.Series, bench: pd.Series, trades: pd.DataFrame | None = None, boot: bool = True) -> dict:
    r = r.astype(float)
    n = len(r)
    eq = (1 + r).cumprod()
    years = n / ANN
    out = dict(
        days=n, start=str(r.index[0]), end=str(r.index[-1]),
        total_return=float(eq.iloc[-1] - 1),
        cagr=float(eq.iloc[-1] ** (1 / years) - 1) if years > 0 else np.nan,
        ann_vol=float(r.std(ddof=1) * np.sqrt(ANN)),
        sharpe=sharpe(r), sortino=sortino(r),
        max_drawdown=max_drawdown(r),
        mean_daily_t=float(r.mean() / (r.std(ddof=1) / np.sqrt(n))) if r.std() > 0 else np.nan,
        active_days=int((r != 0).sum()),
        best_day=float(r.max()),
        total_ex_best_day=float((1 + r.drop(r.idxmax())).prod() - 1),
    )
    out["calmar"] = out["cagr"] / abs(out["max_drawdown"]) if out["max_drawdown"] < 0 else np.nan
    if trades is not None and len(trades):
        tr = trades.ret
        out.update(n_trades=int(len(tr)), win_rate=float((tr > 0).mean()), avg_trade=float(tr.mean()),
                   profit_factor=float(tr[tr > 0].sum() / -tr[tr < 0].sum()) if (tr < 0).any() else np.inf,
                   long_trades=int((trades.side > 0).sum()), short_trades=int((trades.side < 0).sum()))
    else:
        out.update(n_trades=0)
    out.update(alpha_beta(r, bench))
    if boot:
        out.update(block_bootstrap(r))
    return out
