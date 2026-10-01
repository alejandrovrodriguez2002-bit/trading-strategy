#!/usr/bin/env python3
"""
Backtest de dos estrategias intradía sobre el futuro E-mini Nasdaq-100 (NQ,
proxy del US100) con velas de 1 minuto de CME (Databento GLBX.MDP3):

  S1  Momentum intradía con bandas de ruido + trailing stop
      (Zarattini, Aziz & Barbon 2024, SSRN 4824172)
  S2  La primera media hora predice la última media hora + filtro VIX >= 20
      (Gao, Han, Li & Zhou 2018, SSRN 2552752)

Pasos: limpia/valida los datos (backtest/data.py), corre ambas estrategias,
calcula Sharpe, Sortino, alfa y beta vs NQ buy & hold, IC por bootstrap,
pruebas de robustez y genera la curva de capital.

Uso:
    # el CSV crudo vive en la rama data-exports
    git show origin/data-exports:data/databento_NQ_c_0_1m_candles.csv > data/raw_NQ_c_0_1m.csv
    python3 scripts/run_intraday_strategies.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backtest import data as D, metrics as M, strategies as S  # noqa: E402

OUT = ROOT / "results" / "intraday_strategies"
CLEAN = ROOT / "data" / "clean"

BLUE, ORANGE, GRAY, INK, MUTED = "#2a78d6", "#eb6834", "#8a8984", "#0b0b0b", "#52514e"


def pct(x, d=2):
    return "n/a" if x is None or not np.isfinite(x) else f"{x * 100:.{d}f}%"


def num(x, d=2):
    return "n/a" if x is None or not np.isfinite(x) else f"{x:.{d}f}"


def main():
    import argparse
    global OUT, CLEAN
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(ROOT / "data" / "raw_NQ_c_0_1m.csv"))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--clean", default=str(CLEAN))
    args = ap.parse_args()
    OUT, CLEAN = Path(args.out).resolve(), Path(args.clean).resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    CLEAN.mkdir(parents=True, exist_ok=True)

    raw = D.load_raw(args.raw)
    vix = D.load_vix(ROOT / "data" / "vix_daily.csv")
    data = D.build(raw, vix)
    daily = data.daily

    # --- datos limpios para reutilizar -----------------------------------
    rth = pd.concat([data.bars[d].assign(date=d) for d in daily.index[daily.tradable]])
    rth[["Open", "High", "Low", "Close", "Volume", "VWAP", "contract"]].round(4).to_csv(
        CLEAN / "NQ_rth_1m_clean.csv.gz", index_label="Datetime", compression="gzip")
    daily.to_csv(CLEAN / "NQ_daily_flags.csv")

    bench_all = daily.loc[daily.cash_day, "ret_cc"]

    # --- estrategias principales -----------------------------------------
    runs = {
        "S1 bandas de ruido (vol-target, paper)": S.noise_band_momentum(data, sizing="voltarget"),
        "S1 bandas de ruido (1x sin apalancar)": S.noise_band_momentum(data, sizing="unlevered"),
        "S2 1a->última media hora, VIX>=20": S.first_half_hour_momentum(data, vix_min=20),
        "S2 1a->última media hora, sin filtro VIX": S.first_half_hour_momentum(data, vix_min=None),
    }
    s1_start = runs["S1 bandas de ruido (vol-target, paper)"][0].index[0]

    results, curves = {}, {}
    for name, (r, tr) in runs.items():
        res = M.summarize(r.ret, bench_all, tr)
        res["avg_leverage"] = float(r.lev.mean())
        # misma ventana que S1 (después de los 14 días de calentamiento) para comparar
        rc = r.ret[r.index >= s1_start]
        trc = tr[tr.date >= s1_start] if len(tr) else tr
        res["common_window"] = M.summarize(rc, bench_all, trc, boot=False)
        results[name] = res
        curves[name] = r.ret
        tr.to_csv(OUT / f"trades_{name.split()[0]}_{'vt' if 'vol-target' in name else '1x' if '1x' in name else 'vix' if 'VIX>=' in name else 'all'}.csv",
                  index=False)

    bench_window = bench_all[bench_all.index >= curves["S2 1a->última media hora, VIX>=20"].index[0]].dropna()
    results["NQ buy & hold (benchmark)"] = M.summarize(bench_window, bench_all, None)
    results["NQ buy & hold (benchmark)"]["common_window"] = M.summarize(
        bench_window[bench_window.index >= s1_start], bench_all, None, boot=False)

    # --- robustez --------------------------------------------------------
    rob = []
    rob_start = S.noise_band_momentum(data, lookback=20, sizing="unlevered")[0].index[0]
    for lb in (10, 14, 20):
        for sizing in ("voltarget", "unlevered"):
            for ex in ("next_open", "mark_close"):
                for cm in (0.0, 1.0, 2.0):
                    r, tr = S.noise_band_momentum(data, lookback=lb, sizing=sizing, execution=ex,
                                                  cost_pts=cm * S.COST_PTS_PER_SIDE)
                    r = r[r.index >= rob_start]  # ventana común a todos los lookbacks
                    m = M.summarize(r.ret, bench_all, tr[tr.date.isin(r.index)], boot=False)
                    rob.append(dict(strategy="S1", lookback=lb, sizing=sizing, execution=ex, cost_x=cm,
                                    total=m["total_return"], sharpe=m["sharpe"], sortino=m["sortino"],
                                    maxdd=m["max_drawdown"], alpha=m["alpha_ann"], beta=m["beta"], trades=m["n_trades"]))
    for vmin in (None, 15, 20, 25):
        for fd in ("prev_close", "open"):
            for ex in ("next_open", "mark_close"):
                for cm in (0.0, 1.0, 2.0):
                    r, tr = S.first_half_hour_momentum(data, vix_min=vmin, first_def=fd, execution=ex,
                                                       cost_pts=cm * S.COST_PTS_PER_SIDE)
                    m = M.summarize(r.ret, bench_all, tr, boot=False)
                    rob.append(dict(strategy="S2", vix_min=vmin or 0, first_def=fd, execution=ex, cost_x=cm,
                                    total=m["total_return"], sharpe=m["sharpe"], sortino=m["sortino"],
                                    maxdd=m["max_drawdown"], alpha=m["alpha_ann"], beta=m["beta"], trades=m["n_trades"],
                                    win_rate=m.get("win_rate", np.nan)))
    rob = pd.DataFrame(rob)
    rob.to_csv(OUT / "robustness.csv", index=False)

    # sub-periodos: por año calendario si hay más de un año, si no, por mitades
    halves = {}
    for name, r in curves.items():
        years = pd.Index([d.year for d in r.index])
        if years.nunique() > 1:
            parts = [(str(y), r[years == y]) for y in sorted(years.unique())]
        else:
            mid = r.index[len(r) // 2]
            parts = [("1a mitad", r[r.index < mid]), ("2a mitad", r[r.index >= mid])]
        halves[name] = {h: M.summarize(x, bench_all, None, boot=False) for h, x in parts if len(x) > 5}

    with open(OUT / "metrics.json", "w") as f:
        json.dump(dict(results=results, halves=halves, data_log=data.log), f, indent=2, default=str)

    plot_equity(curves, bench_window, OUT / "equity_curve.png")
    write_report(results, halves, rob, data, OUT / "report.md", rob_start, args.raw)
    print((OUT / "report.md").read_text())


def plot_equity(curves, bench, path):
    styles = {
        "S1 bandas de ruido (vol-target, paper)": (BLUE, "-", 2.0),
        "S1 bandas de ruido (1x sin apalancar)": (BLUE, "--", 1.6),
        "S2 1a->última media hora, VIX>=20": (ORANGE, "-", 2.0),
        "S2 1a->última media hora, sin filtro VIX": (ORANGE, "--", 1.6),
    }
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(11, 7.5), sharex=True, gridspec_kw=dict(height_ratios=[3, 1.2]))
    series = {**{k: v for k, v in curves.items()}, "NQ buy & hold": bench}
    ends = sorted((100 * (1 + r.values).prod(), n) for n, r in series.items())
    label_y, last = {}, -np.inf
    gap = 0.035 * (ends[-1][0] - min(100, ends[0][0])) or 1.2
    for v, n in ends:  # separa etiquetas finales que se encimarían
        last = max(v, last + gap)
        label_y[n] = last
    for name, r in series.items():
        color, ls, lw = styles.get(name, (GRAY, "-", 1.4))
        idx = pd.to_datetime(pd.Index(r.index))
        eq = 100 * (1 + r.values).cumprod()
        ax.plot(idx, eq, color=color, ls=ls, lw=lw, label=name)
        ax.annotate(f"{eq[-1]:.1f}", (idx[-1], label_y[name]), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=8.5, color=INK)
        dd = 100 * (eq / np.maximum.accumulate(eq) - 1)
        ax2.plot(idx, dd, color=color, ls=ls, lw=1.2)
    ax.axhline(100, color=MUTED, lw=0.8, alpha=0.5)
    ax.set_title("Curva de capital - NQ (US100) 1 min CME, base 100, neto de costos", loc="left", fontsize=12, color=INK)
    ax.set_ylabel("Capital (base 100)", color=MUTED)
    ax2.set_ylabel("Drawdown (%)", color=MUTED)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    for a in (ax, ax2):
        a.grid(alpha=0.25, lw=0.6)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
        a.tick_params(colors=MUTED, labelsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor="#fcfcfb")
    plt.close(fig)


def alpha_txt(name, m, bold=False):
    if "benchmark" in name:
        return "—"
    a = pct(m["alpha_ann"], 1)
    return f"{'**' + a + '**' if bold else a} ({num(m['alpha_t'])})"


def write_report(results, halves, rob, data, path, rob_start, raw_name):
    L = []
    L.append("# Backtest: momentum intradía en el US100 (futuro NQ, CME, velas de 1 minuto)\n")
    L.append("Generado por `scripts/run_intraday_strategies.py`. Todas las cifras son **netas de costos** "
             f"({S.COST_PTS_PER_SIDE} pt por lado y contrato = 1 tick de slippage + ~2.50 USD de comisión) y "
             "con ejecución en la apertura de la vela siguiente a la señal (sin look-ahead).\n")
    L.append("![Curva de capital](equity_curve.png)\n")
    L.append("## Resultados principales\n")
    L.append("| Estrategia | Ventana | Días | Trades | Retorno total | CAGR | Vol. anual | Sharpe | **Sortino** | Máx. DD | "
             "**Alfa anual** (t) | **Beta** | Win rate | Profit factor | IC 90 % Sharpe | P(media≤0) | Retorno sin el mejor día |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name, m in results.items():
        ci = m.get("sharpe_ci90", [np.nan, np.nan])
        alpha = alpha_txt(name, m, bold=True)
        L.append(f"| {name} | {m['start']} → {m['end']} | {m['days']} | {m['n_trades']} | {pct(m['total_return'])} | "
                 f"{pct(m['cagr'], 1)} | {pct(m['ann_vol'], 1)} | {num(m['sharpe'])} | **{num(m['sortino'])}** | "
                 f"{pct(m['max_drawdown'])} | {alpha} | **{num(m['beta'])}** | "
                 f"{pct(m.get('win_rate', np.nan), 0)} | {num(m.get('profit_factor', np.nan))} | "
                 f"[{num(ci[0])}, {num(ci[1])}] | {num(m.get('prob_mean_le_0', np.nan))} | {pct(m['total_ex_best_day'])} |")
    L.append("\nAlfa y beta: regresión OLS diaria `r_estrategia = α + β·r_NQ` con errores Newey-West (5 rezagos); "
             "α anualizada ×252, entre paréntesis su estadístico t (|t| > 2 ≈ significativo al 5 %). "
             "Benchmark = NQ comprado y mantenido (cierre a cierre de la sesión regular). Sharpe/Sortino con rf = 0 "
             "porque el P&L de un futuro ya es retorno en exceso. Sortino = media / desviación a la baja (MAR = 0) × √252. "
             "IC 90 % y P(media≤0) por bootstrap por bloques (5 000 réplicas, bloque medio de 5 días). "
             + ("CAGR anualiza un periodo de < 1 año: tómalo como referencia, no como expectativa.\n"
                if next(iter(results.values()))["days"] < 252 else "\n"))

    L.append("### Misma ventana para todas (desde que S1 termina su calentamiento de 14 días)\n")
    L.append("| Estrategia | Ventana | Trades | Retorno | Sharpe | Sortino | Máx. DD | Alfa anual (t) | Beta |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for name, m0 in results.items():
        m = m0["common_window"]
        L.append(f"| {name} | {m['start']} → {m['end']} | {m['n_trades']} | {pct(m['total_return'])} | {num(m['sharpe'])} | "
                 f"{num(m['sortino'])} | {pct(m['max_drawdown'])} | {alpha_txt(name, m)} | {num(m['beta'])} |")

    L.append("\n### Estabilidad por sub-periodo\n")
    L.append("| Estrategia | Periodo | Retorno | Sharpe | Sortino | Máx. DD |")
    L.append("|---|---|---|---|---|---|")
    for name, hs in halves.items():
        for h, m in hs.items():
            L.append(f"| {name} | {h} ({m['start']} → {m['end']}) | {pct(m['total_return'])} | {num(m['sharpe'])} | "
                     f"{num(m['sortino'])} | {pct(m['max_drawdown'])} |")

    s1 = rob[rob.strategy == "S1"]
    s2 = rob[rob.strategy == "S2"]
    L.append("\n## Robustez\n")
    L.append("**S1** — 36 variantes (lookback 10/14/20 × sizing vol-target/1x × ejecución siguiente-apertura/precio-de-señal "
             f"× costos 0/1x/2x), todas medidas desde {rob_start} para que la ventana sea idéntica: "
             f"Sharpe mediano {num(s1.sharpe.median())}, rango [{num(s1.sharpe.min())}, {num(s1.sharpe.max())}]; "
             f"{int((s1.total > 0).sum())}/{len(s1)} variantes con retorno positivo.\n")
    piv = s1[(s1.execution == "next_open") & (s1.cost_x == 1.0)].pivot_table(index="lookback", columns="sizing",
                                                                             values=["sharpe", "sortino", "total"])
    L.append("| Lookback | Sharpe vol-target | Sharpe 1x | Sortino vol-target | Sortino 1x | Retorno vol-target | Retorno 1x |")
    L.append("|---|---|---|---|---|---|---|")
    for lb, row in piv.iterrows():
        L.append(f"| {lb} | {num(row[('sharpe', 'voltarget')])} | {num(row[('sharpe', 'unlevered')])} | "
                 f"{num(row[('sortino', 'voltarget')])} | {num(row[('sortino', 'unlevered')])} | "
                 f"{pct(row[('total', 'voltarget')])} | {pct(row[('total', 'unlevered')])} |")
    L.append("\n**S2** — filtro VIX (sin filtro / ≥15 / ≥20 / ≥25) × definición de la primera media hora "
             "(cierre previo→10:00 como en el paper, o 09:30→10:00) × ejecución × costos:\n")
    L.append("| Filtro VIX | 1a media hora | Trades | Win rate | Retorno | Sharpe | Sortino | Alfa anual | Beta |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for _, r in s2[(s2.execution == "next_open") & (s2.cost_x == 1.0)].iterrows():
        L.append(f"| {'sin filtro' if r.vix_min == 0 else '≥ %d' % r.vix_min} | {r.first_def} | {r.trades} | "
                 f"{pct(r.win_rate, 0)} | {pct(r.total)} | {num(r.sharpe)} | {num(r.sortino)} | {pct(r.alpha, 1)} | {num(r.beta)} |")
    L.append("\nTabla completa en `robustness.csv`.\n")

    L.append("## Datos: fuente, limpieza y validación\n")
    L.append("* Fuente: CME Globex vía Databento (`GLBX.MDP3`, `ohlcv-1m`, símbolo continuo `NQ.c.0`), archivo "
             f"`{Path(raw_name).name}` (exportado por el workflow de Databento de este repo). VIX diario: CBOE vía `datasets/finance-vix` (GitHub).")
    L.append("* Solo se usa la sesión regular 09:30-16:00 ET (390 velas/día). Datos limpios en "
             f"`{CLEAN.relative_to(ROOT)}/NQ_rth_1m_clean.csv.gz` y banderas por día en `{CLEAN.relative_to(ROOT)}/NQ_daily_flags.csv`.\n")
    L.append("Bitácora de chequeos:\n")
    for line in data.log:
        L.append(f"* {line}")
    L.append("")
    path.write_text("\n".join(L))


if __name__ == "__main__":
    main()
