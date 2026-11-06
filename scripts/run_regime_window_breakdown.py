#!/usr/bin/env python3
"""Dos pruebas pedidas como continuación del filtro de régimen:

1. **Ventana de persistencia** (`regime_window_bars`): en vez de exigir
   el filtro solo en la vela exacta de rompimiento, exigirlo en las N
   velas ANTERIORES también (persistencia, no solo un flash puntual).
   Barre N en {1, 3, 5, 10, 20, 50} x los dos umbrales (`green_only`,
   `not_red`) x 3 niveles x 2 instrumentos, train/test.

2. **Desglose exploratorio por régimen**: en vez de solo filtrar (pasa/no
   pasa), mirar qué patrón real hay en los trades YA EXISTENTES (sin
   filtrar) según el régimen exacto -1/0/1 que tenían al momento del
   rompimiento -- win rate, R promedio, profit factor por cada uno de
   los 3 estados, para ver si hay una diferencia real entre operar en
   NEUTRAL vs ESTRUCTURADO (no solo "verde sí/no").

Genera:
  - results/regime_window_breakdown/window_sweep_report.md (+ .json)
  - results/regime_window_breakdown/window_sweep_sortino.png
  - results/regime_window_breakdown/regime_breakdown_<instrumento>.png

Uso:
    python scripts/run_regime_window_breakdown.py
"""
import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.data import load_csv  # noqa: E402
from src.market_regime import compute_regime  # noqa: E402
from src.metrics import compute_metrics  # noqa: E402
from src.simple_orb import SimpleORBConfig, run_backtest_simple  # noqa: E402

SOURCES = {
    "QQQ": "data/databento_QQQ_5m_candles.csv",
    "US100 (proxy NQ)": "data/databento_NQ_c_0_5m_candles.csv",
}

LEVELS = {
    "apertura (OR30)": dict(range_source="opening_range", or_minutes=30, session_only=True, volume_filter_enabled=False),
    "día anterior (PDH/PDL)": dict(range_source="prev_session", session_only=True, volume_filter_enabled=False),
    "4 horas": dict(range_source="4h_candle", session_only=False, volume_filter_enabled=False),
}

BASE_RECIPE = dict(
    direction_mode="fade", sl_mode="or_opposite", tp_mode="r_multiple", tp_r_multiple=1.5,
    sl_buffer_pct=0.03, trend_filter_enabled=False, max_leverage=1.0,
)

GATE_MODES = ["green_only", "not_red"]
WINDOW_BARS_GRID = [1, 3, 5, 10, 20, 50]
REGIME_LABELS = {-1: "VOLÁTIL (rojo)", 0: "NEUTRAL", 1: "ESTRUCTURADO (verde)"}
REGIME_COLORS = {-1: "#c0392b", 0: "#7f8fa6", 1: "#27ae60"}


def _split_train_test(df):
    dates = sorted(set(df.index.date))
    split_date = dates[len(dates) // 2]
    return df[df.index.date < split_date], df[df.index.date >= split_date], split_date


def _cfg_for(level_params):
    return SimpleORBConfig(**BASE_RECIPE, **level_params)


def _bucket_stats(trades: pd.DataFrame) -> dict:
    """Estadísticas descriptivas simples (no necesitan curva de equity
    diaria) para un subconjunto de trades ya filtrado por régimen."""
    n = len(trades)
    if n == 0:
        return {"num_trades": 0, "win_rate_pct": np.nan, "avg_r_multiple": np.nan, "profit_factor": np.nan}
    wins = trades[trades["pnl"] > 0]
    losses = trades[trades["pnl"] <= 0]
    gross_win = wins["pnl"].sum()
    gross_loss = losses["pnl"].sum()
    pf = (gross_win / abs(gross_loss)) if gross_loss != 0 else np.inf
    return {
        "num_trades": n,
        "win_rate_pct": round(100 * len(wins) / n, 1),
        "avg_r_multiple": round(float(trades["r_multiple"].mean()), 3),
        "profit_factor": round(float(pf), 2) if np.isfinite(pf) else pf,
    }


def run_window_sweep(sources, levels):
    rows = []
    for instrument, path in sources.items():
        if not Path(path).exists():
            print(f"[{instrument}] archivo no encontrado, se omite: {path}")
            continue
        df = load_csv(path, tz="America/New_York")
        regime_full = compute_regime(df)["regime"]
        train_df, test_df, split_date = _split_train_test(df)
        train_regime, test_regime, _ = _split_train_test(regime_full.to_frame("regime"))
        train_regime, test_regime = train_regime["regime"], test_regime["regime"]

        print(f"\n=== {instrument} ===")
        for level_name, level_params in levels.items():
            cfg = _cfg_for(level_params)
            trades_un_train, ec_un_train = run_backtest_simple(train_df, cfg)
            m_un_train = compute_metrics(trades_un_train, ec_un_train)
            trades_un_test, ec_un_test = run_backtest_simple(test_df, cfg)
            m_un_test = compute_metrics(trades_un_test, ec_un_test)
            print(f"  {level_name}: sin filtro train pf={m_un_train['profit_factor']} "
                  f"test pf={m_un_test['profit_factor']}")

            for mode in GATE_MODES:
                for w in WINDOW_BARS_GRID:
                    tt, ec_t = run_backtest_simple(train_df, cfg, regime=train_regime, regime_mode=mode,
                                                    regime_window_bars=w)
                    mt = compute_metrics(tt, ec_t)
                    tt2, ec_t2 = run_backtest_simple(test_df, cfg, regime=test_regime, regime_mode=mode,
                                                      regime_window_bars=w)
                    mt2 = compute_metrics(tt2, ec_t2)
                    rows.append({
                        "instrument": instrument, "level": level_name, "regime_mode": mode, "window_bars": w,
                        "train": mt, "test": mt2,
                    })
                    print(f"    [{mode}, N={w:>2}] train n={mt['num_trades']:>3} pf={mt['profit_factor']!s:>5} "
                          f"sortino={mt['sortino_ratio']!s:>7}  |  test n={mt2['num_trades']:>3} "
                          f"pf={mt2['profit_factor']!s:>5} sortino={mt2['sortino_ratio']!s:>7}")
    return rows


def run_regime_breakdown(sources, levels):
    rows = []
    for instrument, path in sources.items():
        if not Path(path).exists():
            continue
        df = load_csv(path, tz="America/New_York")
        regime_full = compute_regime(df)["regime"]

        for level_name, level_params in levels.items():
            cfg = _cfg_for(level_params)
            trades, _ = run_backtest_simple(df, cfg)
            if trades.empty:
                continue
            # régimen en la vela de entrada (== vela de rompimiento en este motor)
            trades = trades.copy()
            trades["regime_at_entry"] = regime_full.reindex(trades["entry_time"]).values

            for bucket in (-1, 0, 1):
                sub = trades[trades["regime_at_entry"] == bucket]
                stats = _bucket_stats(sub)
                rows.append({
                    "instrument": instrument, "level": level_name, "regime_bucket": bucket,
                    "regime_label": REGIME_LABELS[bucket], **stats,
                })
    return rows


def _plot_window_sweep(outdir, rows):
    instruments = sorted(set(r["instrument"] for r in rows))
    levels = list(LEVELS.keys())
    fig, axes = plt.subplots(len(levels), len(instruments), figsize=(7 * len(instruments), 4 * len(levels)),
                              sharex=True)
    if len(instruments) == 1:
        axes = axes.reshape(len(levels), 1)
    if len(levels) == 1:
        axes = axes.reshape(1, len(instruments))

    for row_i, level in enumerate(levels):
        for col_j, instrument in enumerate(instruments):
            ax = axes[row_i, col_j]
            subset = [r for r in rows if r["instrument"] == instrument and r["level"] == level]
            # línea de referencia: sin filtro (constante, el mismo valor para cualquier N/modo)
            un_rows = [r for r in subset if r["window_bars"] == 1 and r["regime_mode"] == "green_only"]
            for mode, color in zip(GATE_MODES, ["#2980b9", "#8e44ad"]):
                mode_rows = sorted([r for r in subset if r["regime_mode"] == mode], key=lambda r: r["window_bars"])
                xs = [r["window_bars"] for r in mode_rows]
                ys = [r["test"]["sortino_ratio"] for r in mode_rows]
                ax.plot(xs, ys, marker="o", color=color, label=f"{mode} (test)")
            ax.axhline(0.0, color="red", linestyle="--", linewidth=1)
            ax.set_title(f"{instrument} -- {level}", fontsize=9)
            ax.set_xlabel("Ventana de persistencia N (velas)")
            ax.set_ylabel("Sortino (test)")
            ax.legend(fontsize=7)
            ax.grid(alpha=0.3)
    fig.suptitle("Sortino fuera de muestra vs. ventana de persistencia del régimen (N velas antes del rompimiento)")
    fig.tight_layout()
    fig.savefig(outdir / "window_sweep_sortino.png", dpi=140)
    plt.close(fig)


def _plot_regime_breakdown(outdir, rows):
    instruments = sorted(set(r["instrument"] for r in rows))
    levels = list(LEVELS.keys())
    for instrument in instruments:
        fig, axes = plt.subplots(1, len(levels), figsize=(6 * len(levels), 4.8), sharey=False)
        if len(levels) == 1:
            axes = [axes]
        for ax, level in zip(axes, levels):
            subset = {r["regime_bucket"]: r for r in rows if r["instrument"] == instrument and r["level"] == level}
            buckets = [-1, 0, 1]
            win_rates = [subset[b]["win_rate_pct"] if b in subset else np.nan for b in buckets]
            counts = [subset[b]["num_trades"] if b in subset else 0 for b in buckets]
            colors = [REGIME_COLORS[b] for b in buckets]
            bars = ax.bar([REGIME_LABELS[b] for b in buckets], win_rates, color=colors)
            for bar, c, wr in zip(bars, counts, win_rates):
                label = f"n={c}" if np.isfinite(wr) else "sin datos"
                ax.text(bar.get_x() + bar.get_width() / 2, (wr if np.isfinite(wr) else 0) + 2, label,
                        ha="center", fontsize=8)
            ax.axhline(50.0, color="black", linestyle=":", linewidth=1)
            ax.set_title(level, fontsize=9)
            ax.set_ylabel("Win rate %")
            ax.set_ylim(0, 100)
            ax.tick_params(axis="x", labelsize=8, rotation=10)
            ax.grid(axis="y", alpha=0.3)
        fig.suptitle(f"Win rate por régimen en la vela de rompimiento ({instrument}, histórico completo, sin filtrar)")
        fig.tight_layout()
        safe_name = instrument.replace(" ", "_").replace("(", "").replace(")", "")
        fig.savefig(outdir / f"regime_breakdown_{safe_name}.png", dpi=140)
        plt.close(fig)


def main():
    outdir = Path("results/regime_window_breakdown")
    outdir.mkdir(parents=True, exist_ok=True)

    print("### 1) Barrido de ventana de persistencia ###")
    sweep_rows = run_window_sweep(SOURCES, LEVELS)
    with open(outdir / "window_sweep_results.json", "w") as f:
        json.dump(sweep_rows, f, indent=2, default=str)
    _plot_window_sweep(outdir, sweep_rows)

    print("\n### 2) Desglose por régimen (rojo/neutral/verde), sin filtrar ###")
    breakdown_rows = run_regime_breakdown(SOURCES, LEVELS)
    for r in breakdown_rows:
        print(f"  {r['instrument']:20} {r['level']:25} {r['regime_label']:22} "
              f"n={r['num_trades']:>4} wr={r['win_rate_pct']!s:>5} avgR={r['avg_r_multiple']!s:>6} "
              f"pf={r['profit_factor']!s:>5}")
    with open(outdir / "regime_breakdown_results.json", "w") as f:
        json.dump(breakdown_rows, f, indent=2, default=str)
    _plot_regime_breakdown(outdir, breakdown_rows)

    # ---------------- Reporte markdown ----------------
    with open(outdir / "window_sweep_report.md", "w") as f:
        f.write("# Ventana de persistencia del régimen + desglose rojo/neutral/verde\n\n")
        f.write("## 1) Barrido de ventana de persistencia (N velas antes del rompimiento)\n\n")
        f.write("Mejor Sortino (test) por nivel/instrumento/modo, con la ventana N que lo logra:\n\n")
        instruments = sorted(set(r["instrument"] for r in sweep_rows))
        for instrument in instruments:
            f.write(f"### {instrument}\n\n")
            f.write("| Nivel | Modo | Mejor N | Sortino (test) | Profit factor (test) | Trades (test) |\n")
            f.write("|---|---|---|---|---|---|\n")
            for level in LEVELS:
                for mode in GATE_MODES:
                    subset = [r for r in sweep_rows if r["instrument"] == instrument and r["level"] == level
                              and r["regime_mode"] == mode]
                    if not subset:
                        continue
                    best = max(subset, key=lambda r: r["test"]["sortino_ratio"] if np.isfinite(
                        r["test"]["sortino_ratio"]) else -999)
                    f.write(f"| {level} | {mode} | {best['window_bars']} | {best['test']['sortino_ratio']} | "
                            f"{best['test']['profit_factor']} | {best['test']['num_trades']} |\n")
            f.write("\n")

        f.write("## 2) Desglose por régimen en la vela de rompimiento (sin filtrar, histórico completo)\n\n")
        for instrument in instruments:
            f.write(f"### {instrument}\n\n")
            f.write("| Nivel | Régimen | Trades | Win rate % | R promedio | Profit factor |\n")
            f.write("|---|---|---|---|---|---|\n")
            for r in breakdown_rows:
                if r["instrument"] != instrument:
                    continue
                f.write(f"| {r['level']} | {r['regime_label']} | {r['num_trades']} | {r['win_rate_pct']} | "
                        f"{r['avg_r_multiple']} | {r['profit_factor']} |\n")
            f.write("\n")

    print(f"\nReporte y gráficas guardados en {outdir}/")


if __name__ == "__main__":
    main()
