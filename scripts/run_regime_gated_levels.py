#!/usr/bin/env python3
"""Prueba pedida: usar "Market Regime v7" (indicador subido por el
usuario, portado a Python en `src/market_regime.py`) como FILTRO -- solo
tomar el trade cuando el régimen está en ESTRUCTURADO (verde, +1) -- en
la misma receta de fade ya validada (SL en la mecha real + TP de 1.5R
fijo, sin filtro de tendencia ni de volumen, `max_leverage=1.0`), aplicada
a TRES niveles de referencia distintos:

  - "apertura" -> rango de apertura de 30 min de NY (`range_source="opening_range"`, or30)
  - "día anterior" -> PDH/PDL (`range_source="prev_session"`)
  - "4 horas" -> high/low de la última vela de 4h cerrada (`range_source="4h_candle"`)

Sobre datos reales de QQQ y NQ (proxy de US100, ver README.md). Para cada
(instrumento, nivel) se corre la receta SIN filtro de régimen (ungated,
el baseline ya conocido) y CON el filtro (gated, régimen==+1 en la vela
de rompimiento), en train y test (split honesto por fecha, mitad/mitad).

Genera:
  - results/regime_gated_levels/regime_gated_levels_report.md (+ .json)
  - results/regime_gated_levels/liquidity_by_level.png (frecuencia de
    rompimientos por nivel, y qué fracción ocurre en régimen verde)
  - results/regime_gated_levels/profitability_by_level.png (profit
    factor y Sortino, gated vs ungated, test, por nivel e instrumento)
  - results/regime_gated_levels/equity_curves_<instrumento>.png (curvas
    de equity gated vs ungated por nivel, sobre el historial completo)

Uso:
    python scripts/run_regime_gated_levels.py
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


def _split_train_test(df):
    dates = sorted(set(df.index.date))
    split_date = dates[len(dates) // 2]
    return df[df.index.date < split_date], df[df.index.date >= split_date], split_date


def _cfg_for(level_params):
    return SimpleORBConfig(**BASE_RECIPE, **level_params)


def main():
    outdir = Path("results/regime_gated_levels")
    outdir.mkdir(parents=True, exist_ok=True)

    rows = []
    equity_curves = {}  # (instrument, level, gated) -> pd.Series, sobre el historial completo

    for instrument, path in SOURCES.items():
        if not Path(path).exists():
            print(f"[{instrument}] archivo no encontrado, se omite: {path}")
            continue
        df = load_csv(path, tz="America/New_York")
        regime_full = compute_regime(df)["regime"]
        n_days = len(set(df.index.date))
        print(f"\n=== {instrument}: {len(df)} velas, {n_days} días ===")
        green_pct = round((regime_full == 1).mean() * 100, 1)
        print(f"  régimen ESTRUCTURADO (verde) en el {green_pct}% de las velas")

        train_df, test_df, split_date = _split_train_test(df)
        train_regime, test_regime, _ = _split_train_test(regime_full.to_frame("regime"))
        train_regime, test_regime = train_regime["regime"], test_regime["regime"]

        for level_name, level_params in LEVELS.items():
            cfg = _cfg_for(level_params)
            print(f"  -- nivel: {level_name} --")

            for split_label, d, r in [("train", train_df, train_regime), ("test", test_df, test_regime)]:
                trades_un, ec_un = run_backtest_simple(d, cfg)
                m_un = compute_metrics(trades_un, ec_un)

                trades_g, ec_g = run_backtest_simple(d, cfg, regime=r)
                m_g = compute_metrics(trades_g, ec_g)

                kept_pct = round(100 * m_g["num_trades"] / m_un["num_trades"], 1) if m_un["num_trades"] else None
                print(f"     [{split_label}] ungated: n={m_un['num_trades']:>3} pf={m_un['profit_factor']!s:>5} "
                      f"sortino={m_un['sortino_ratio']!s:>7}  |  gated: n={m_g['num_trades']:>3} "
                      f"pf={m_g['profit_factor']!s:>5} sortino={m_g['sortino_ratio']!s:>7}  (retiene {kept_pct}%)")

                rows.append({
                    "instrument": instrument, "level": level_name, "split": split_label,
                    "ungated": m_un, "gated": m_g, "kept_pct": kept_pct,
                })

            # curvas de equity sobre el historial COMPLETO (no solo train/test) para el gráfico
            trades_un_full, ec_un_full = run_backtest_simple(df, cfg)
            trades_g_full, ec_g_full = run_backtest_simple(df, cfg, regime=regime_full)
            equity_curves[(instrument, level_name, "ungated")] = ec_un_full
            equity_curves[(instrument, level_name, "gated")] = ec_g_full

    with open(outdir / "regime_gated_levels_results.json", "w") as f:
        json.dump(rows, f, indent=2, default=str)

    _write_report(outdir, rows)
    _plot_liquidity(outdir, rows)
    _plot_profitability(outdir, rows)
    _plot_equity_curves(outdir, equity_curves)

    print(f"\nReporte y gráficas guardados en {outdir}/")


def _write_report(outdir, rows):
    md_path = outdir / "regime_gated_levels_report.md"
    cols = ["num_trades", "win_rate_pct", "profit_factor", "sortino_ratio", "total_return_pct", "max_drawdown_pct"]
    with open(md_path, "w") as f:
        f.write("# Filtro de régimen (Market Regime v7) por nivel\n\n")
        f.write(
            "Misma receta fade ya validada (SL en la mecha real, TP=1.5R fijo, sin filtros de "
            "tendencia/volumen, `max_leverage=1.0`) aplicada a 3 niveles de referencia (apertura "
            "OR30, PDH/PDL, vela de 4h), con y sin el filtro de régimen "
            "(`Market Regime v7` portado a Python, solo se opera en ESTRUCTURADO/verde). Split "
            "honesto train/test por fecha.\n\n"
        )
        for r in rows:
            f.write(f"## {r['instrument']} -- {r['level']} ({r['split']})\n\n")
            f.write(f"Retiene {r['kept_pct']}% de los trades ungated tras el filtro de régimen.\n\n")
            f.write("| | " + " | ".join(cols) + " |\n")
            f.write("|---|" + "---|" * len(cols) + "\n")
            f.write("| sin filtro | " + " | ".join(str(r["ungated"][c]) for c in cols) + " |\n")
            f.write("| con filtro | " + " | ".join(str(r["gated"][c]) for c in cols) + " |\n\n")


def _plot_liquidity(outdir, rows):
    """Frecuencia de trades (ungated) por nivel/instrumento (train+test combinados)
    y qué fracción se retiene con el filtro de régimen -- "liquidez" = cuántas
    veces ese nivel efectivamente se rompe y genera una operación."""
    by_key = {}
    for r in rows:
        key = (r["instrument"], r["level"])
        by_key.setdefault(key, {"ungated": 0, "gated": 0})
        by_key[key]["ungated"] += r["ungated"]["num_trades"]
        by_key[key]["gated"] += r["gated"]["num_trades"]

    instruments = sorted(set(k[0] for k in by_key))
    levels = list(LEVELS.keys())
    fig, axes = plt.subplots(1, len(instruments), figsize=(6.5 * len(instruments), 4.8), sharey=False)
    if len(instruments) == 1:
        axes = [axes]
    x = np.arange(len(levels))
    width = 0.35
    for ax, instrument in zip(axes, instruments):
        ungated_vals = [by_key.get((instrument, lvl), {}).get("ungated", 0) for lvl in levels]
        gated_vals = [by_key.get((instrument, lvl), {}).get("gated", 0) for lvl in levels]
        ax.bar(x - width / 2, ungated_vals, width, label="Sin filtro de régimen", color="#7f8fa6")
        ax.bar(x + width / 2, gated_vals, width, label="Con filtro (solo verde)", color="#27ae60")
        for i, (u, g) in enumerate(zip(ungated_vals, gated_vals)):
            pct = round(100 * g / u, 0) if u else 0
            ax.text(i + width / 2, g + max(ungated_vals) * 0.02, f"{pct:.0f}%", ha="center", fontsize=8)
        ax.set_xticks(x)
        ax.set_xticklabels(levels, rotation=15, ha="right", fontsize=8)
        ax.set_title(instrument, fontsize=10)
        ax.set_ylabel("Trades totales (train+test)")
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Liquidez por nivel: frecuencia de rompimientos operables, con y sin filtro de régimen")
    fig.tight_layout()
    fig.savefig(outdir / "liquidity_by_level.png", dpi=140)
    plt.close(fig)


def _plot_profitability(outdir, rows):
    """Profit factor y Sortino (TEST, fuera de muestra) gated vs ungated, por nivel/instrumento."""
    test_rows = [r for r in rows if r["split"] == "test"]
    instruments = sorted(set(r["instrument"] for r in test_rows))
    levels = list(LEVELS.keys())

    fig, axes = plt.subplots(2, len(instruments), figsize=(6.5 * len(instruments), 8.5), sharex=True)
    if len(instruments) == 1:
        axes = axes.reshape(2, 1)

    for col, instrument in enumerate(instruments):
        by_level = {r["level"]: r for r in test_rows if r["instrument"] == instrument}
        x = np.arange(len(levels))
        width = 0.35

        pf_un = [by_level[lvl]["ungated"]["profit_factor"] if lvl in by_level else np.nan for lvl in levels]
        pf_g = [by_level[lvl]["gated"]["profit_factor"] if lvl in by_level else np.nan for lvl in levels]
        pf_un = [v if isinstance(v, (int, float)) and np.isfinite(v) else 0 for v in pf_un]
        pf_g = [v if isinstance(v, (int, float)) and np.isfinite(v) else 0 for v in pf_g]

        ax_pf = axes[0, col]
        ax_pf.bar(x - width / 2, pf_un, width, label="Sin filtro", color="#7f8fa6")
        ax_pf.bar(x + width / 2, pf_g, width, label="Con filtro de régimen", color="#2980b9")
        ax_pf.axhline(1.0, color="red", linestyle="--", linewidth=1, label="Profit factor = 1.0")
        ax_pf.set_title(f"{instrument} -- Profit factor (test)", fontsize=10)
        ax_pf.set_xticks(x)
        ax_pf.set_xticklabels(levels, rotation=15, ha="right", fontsize=8)
        ax_pf.legend(fontsize=7)
        ax_pf.grid(axis="y", alpha=0.3)

        sortino_un = [by_level[lvl]["ungated"]["sortino_ratio"] if lvl in by_level else np.nan for lvl in levels]
        sortino_g = [by_level[lvl]["gated"]["sortino_ratio"] if lvl in by_level else np.nan for lvl in levels]

        ax_s = axes[1, col]
        ax_s.bar(x - width / 2, sortino_un, width, label="Sin filtro", color="#7f8fa6")
        ax_s.bar(x + width / 2, sortino_g, width, label="Con filtro de régimen", color="#2980b9")
        ax_s.axhline(0.0, color="red", linestyle="--", linewidth=1)
        ax_s.set_title(f"{instrument} -- Sortino ratio (test)", fontsize=10)
        ax_s.set_xticks(x)
        ax_s.set_xticklabels(levels, rotation=15, ha="right", fontsize=8)
        ax_s.legend(fontsize=7)
        ax_s.grid(axis="y", alpha=0.3)

    fig.suptitle("Rentabilidad fuera de muestra (test) por nivel: con y sin filtro de régimen")
    fig.tight_layout()
    fig.savefig(outdir / "profitability_by_level.png", dpi=140)
    plt.close(fig)


def _plot_equity_curves(outdir, equity_curves):
    instruments = sorted(set(k[0] for k in equity_curves))
    for instrument in instruments:
        levels = [lvl for (inst, lvl, _) in equity_curves if inst == instrument]
        levels = list(dict.fromkeys(levels))
        fig, axes = plt.subplots(1, len(levels), figsize=(6 * len(levels), 4.5), sharey=False)
        if len(levels) == 1:
            axes = [axes]
        for ax, level in zip(axes, levels):
            ec_un = equity_curves.get((instrument, level, "ungated"))
            ec_g = equity_curves.get((instrument, level, "gated"))
            if ec_un is not None:
                ax.plot(ec_un.index, ec_un.values, label="Sin filtro", color="#7f8fa6")
            if ec_g is not None:
                ax.plot(ec_g.index, ec_g.values, label="Con filtro de régimen", color="#2980b9")
            ax.set_title(level, fontsize=9)
            ax.legend(fontsize=7)
            ax.grid(alpha=0.3)
            ax.tick_params(axis="x", labelrotation=30, labelsize=7)
        fig.suptitle(f"Curva de equity ({instrument}, historial completo) por nivel")
        fig.tight_layout()
        safe_name = instrument.replace(" ", "_").replace("(", "").replace(")", "")
        fig.savefig(outdir / f"equity_curves_{safe_name}.png", dpi=140)
        plt.close(fig)


if __name__ == "__main__":
    main()
