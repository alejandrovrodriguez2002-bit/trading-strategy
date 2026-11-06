#!/usr/bin/env python3
"""Prueba pedida: usar "Market Regime v7" (indicador subido por el
usuario, portado a Python en `src/market_regime.py`) como FILTRO -- en
la misma receta de fade ya validada (SL en la mecha real + TP de 1.5R
fijo, sin filtro de tendencia ni de volumen, `max_leverage=1.0`), aplicada
a TRES niveles de referencia distintos:

  - "apertura" -> rango de apertura de 30 min de NY (`range_source="opening_range"`, or30)
  - "día anterior" -> PDH/PDL (`range_source="prev_session"`)
  - "4 horas" -> high/low de la última vela de 4h cerrada (`range_source="4h_candle"`)

Tres umbrales de filtro (`GATE_MODES`):
  - "green_only": exige régimen exacto +1 (ESTRUCTURADO/verde) en la
    vela de rompimiento -- la primera versión probada.
  - "not_red": permite +1 (verde) O 0 (neutral); solo bloquea -1
    (VOLÁTIL/rojo) -- umbral menos exigente, pedido como variante.
  - "red_only": exige -1 (VOLÁTIL/rojo) exacto -- lo opuesto a
    "green_only". Surgió de desglosar los trades sin filtrar por el
    régimen en la vela de rompimiento (ver
    `scripts/run_regime_window_breakdown.py`): en esta estrategia de
    FADE, el régimen "rojo" suele ser donde mejor funciona, no el verde.
    Confirmado con split train/test: en apertura (OR30) sobre US100/NQ,
    el profit factor sube de 1.43 (sin filtro) a 2.08 en test (31
    trades, consistente con 2.29 en train) -- la única mejora real
    encontrada en toda esta exploración de régimen.

Sobre datos reales de QQQ y NQ (proxy de US100, ver README.md), en train
y test (split honesto por fecha, mitad/mitad).

Genera:
  - results/regime_gated_levels/regime_gated_levels_report.md (+ .json)
  - results/regime_gated_levels/liquidity_by_level.png
  - results/regime_gated_levels/profitability_by_level.png
  - results/regime_gated_levels/equity_curves_<instrumento>.png

Uso:
    python scripts/run_regime_gated_levels.py
"""
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

GATE_MODES = ["green_only", "not_red", "red_only"]
GATE_LABELS = {"green_only": "Solo verde", "not_red": "No rojo (verde+neutral)", "red_only": "Solo rojo"}
GATE_COLORS = {"green_only": "#2980b9", "not_red": "#8e44ad", "red_only": "#c0392b"}


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
    equity_curves = {}  # (instrument, level, variant) -> pd.Series, sobre el historial completo

    for instrument, path in SOURCES.items():
        if not Path(path).exists():
            print(f"[{instrument}] archivo no encontrado, se omite: {path}")
            continue
        df = load_csv(path, tz="America/New_York")
        regime_full = compute_regime(df)["regime"]
        n_days = len(set(df.index.date))
        print(f"\n=== {instrument}: {len(df)} velas, {n_days} días ===")
        green_pct = round((regime_full == 1).mean() * 100, 1)
        not_red_pct = round((regime_full != -1).mean() * 100, 1)
        print(f"  régimen verde: {green_pct}% del tiempo | no-rojo (verde+neutral): {not_red_pct}% del tiempo")

        train_df, test_df, split_date = _split_train_test(df)
        train_regime, test_regime, _ = _split_train_test(regime_full.to_frame("regime"))
        train_regime, test_regime = train_regime["regime"], test_regime["regime"]

        for level_name, level_params in LEVELS.items():
            cfg = _cfg_for(level_params)
            print(f"  -- nivel: {level_name} --")

            for split_label, d, r in [("train", train_df, train_regime), ("test", test_df, test_regime)]:
                trades_un, ec_un = run_backtest_simple(d, cfg)
                m_un = compute_metrics(trades_un, ec_un)
                print(f"     [{split_label}] sin filtro: n={m_un['num_trades']:>3} "
                      f"pf={m_un['profit_factor']!s:>5} sortino={m_un['sortino_ratio']!s:>7}")

                gated = {}
                for mode in GATE_MODES:
                    trades_g, ec_g = run_backtest_simple(d, cfg, regime=r, regime_mode=mode)
                    m_g = compute_metrics(trades_g, ec_g)
                    kept_pct = round(100 * m_g["num_trades"] / m_un["num_trades"], 1) if m_un["num_trades"] else None
                    gated[mode] = {"metrics": m_g, "kept_pct": kept_pct}
                    print(f"       [{GATE_LABELS[mode]}]: n={m_g['num_trades']:>3} "
                          f"pf={m_g['profit_factor']!s:>5} sortino={m_g['sortino_ratio']!s:>7}  "
                          f"(retiene {kept_pct}%)")

                rows.append({
                    "instrument": instrument, "level": level_name, "split": split_label,
                    "ungated": m_un, "gated": gated,
                })

            # curvas de equity sobre el historial COMPLETO para el gráfico
            trades_un_full, ec_un_full = run_backtest_simple(df, cfg)
            equity_curves[(instrument, level_name, "ungated")] = ec_un_full
            for mode in GATE_MODES:
                _, ec_g_full = run_backtest_simple(df, cfg, regime=regime_full, regime_mode=mode)
                equity_curves[(instrument, level_name, mode)] = ec_g_full

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
        f.write("# Filtro de régimen (Market Regime v7) por nivel -- dos umbrales\n\n")
        f.write(
            "Misma receta fade ya validada (SL en la mecha real, TP=1.5R fijo, sin filtros de "
            "tendencia/volumen, `max_leverage=1.0`) aplicada a 3 niveles de referencia (apertura "
            "OR30, PDH/PDL, vela de 4h), con y sin el filtro de régimen (`Market Regime v7` "
            "portado a Python), en dos umbrales: **solo verde** (régimen == +1 exacto) y "
            "**no rojo** (régimen != -1, permite verde o neutral). Split honesto train/test por "
            "fecha.\n\n"
        )
        for r in rows:
            f.write(f"## {r['instrument']} -- {r['level']} ({r['split']})\n\n")
            f.write("| | " + " | ".join(cols) + " |\n")
            f.write("|---|" + "---|" * len(cols) + "\n")
            f.write("| sin filtro | " + " | ".join(str(r["ungated"][c]) for c in cols) + " |\n")
            for mode in GATE_MODES:
                g = r["gated"][mode]
                label = f"{GATE_LABELS[mode]} (retiene {g['kept_pct']}%)"
                f.write(f"| {label} | " + " | ".join(str(g["metrics"][c]) for c in cols) + " |\n")
            f.write("\n")


def _plot_liquidity(outdir, rows):
    by_key = {}
    for r in rows:
        key = (r["instrument"], r["level"])
        acc = by_key.setdefault(key, {"ungated": 0, **{m: 0 for m in GATE_MODES}})
        acc["ungated"] += r["ungated"]["num_trades"]
        for mode in GATE_MODES:
            acc[mode] += r["gated"][mode]["metrics"]["num_trades"]

    instruments = sorted(set(k[0] for k in by_key))
    levels = list(LEVELS.keys())
    n_bars = 1 + len(GATE_MODES)
    fig, axes = plt.subplots(1, len(instruments), figsize=(7 * len(instruments), 4.8), sharey=False)
    if len(instruments) == 1:
        axes = [axes]
    x = np.arange(len(levels))
    width = 0.8 / n_bars
    for ax, instrument in zip(axes, instruments):
        ungated_vals = [by_key.get((instrument, lvl), {}).get("ungated", 0) for lvl in levels]
        ax.bar(x - width, ungated_vals, width, label="Sin filtro", color="#7f8fa6")
        for j, mode in enumerate(GATE_MODES):
            vals = [by_key.get((instrument, lvl), {}).get(mode, 0) for lvl in levels]
            ax.bar(x + j * width, vals, width, label=GATE_LABELS[mode], color=GATE_COLORS[mode])
            for i, (u, v) in enumerate(zip(ungated_vals, vals)):
                pct = round(100 * v / u, 0) if u else 0
                ax.text(i + j * width, v + max(ungated_vals) * 0.02, f"{pct:.0f}%", ha="center", fontsize=7)
        ax.set_xticks(x)
        ax.set_xticklabels(levels, rotation=15, ha="right", fontsize=8)
        ax.set_title(instrument, fontsize=10)
        ax.set_ylabel("Trades totales (train+test)")
        ax.legend(fontsize=7)
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Liquidez por nivel: frecuencia de rompimientos operables, por umbral de régimen")
    fig.tight_layout()
    fig.savefig(outdir / "liquidity_by_level.png", dpi=140)
    plt.close(fig)


def _plot_profitability(outdir, rows):
    """Profit factor y Sortino (TEST, fuera de muestra), por nivel/instrumento/umbral."""
    test_rows = [r for r in rows if r["split"] == "test"]
    instruments = sorted(set(r["instrument"] for r in test_rows))
    levels = list(LEVELS.keys())
    n_bars = 1 + len(GATE_MODES)

    fig, axes = plt.subplots(2, len(instruments), figsize=(7 * len(instruments), 8.5), sharex=True)
    if len(instruments) == 1:
        axes = axes.reshape(2, 1)

    def _clean(vals):
        return [v if isinstance(v, (int, float)) and np.isfinite(v) else 0 for v in vals]

    for col, instrument in enumerate(instruments):
        by_level = {r["level"]: r for r in test_rows if r["instrument"] == instrument}
        x = np.arange(len(levels))
        width = 0.8 / n_bars

        pf_un = _clean([by_level[lvl]["ungated"]["profit_factor"] if lvl in by_level else np.nan for lvl in levels])
        ax_pf = axes[0, col]
        ax_pf.bar(x - width, pf_un, width, label="Sin filtro", color="#7f8fa6")
        for j, mode in enumerate(GATE_MODES):
            pf_g = _clean([by_level[lvl]["gated"][mode]["metrics"]["profit_factor"] if lvl in by_level else np.nan
                           for lvl in levels])
            ax_pf.bar(x + j * width, pf_g, width, label=GATE_LABELS[mode], color=GATE_COLORS[mode])
        ax_pf.axhline(1.0, color="red", linestyle="--", linewidth=1, label="Profit factor = 1.0")
        ax_pf.set_title(f"{instrument} -- Profit factor (test)", fontsize=10)
        ax_pf.set_xticks(x)
        ax_pf.set_xticklabels(levels, rotation=15, ha="right", fontsize=8)
        ax_pf.legend(fontsize=7)
        ax_pf.grid(axis="y", alpha=0.3)

        sortino_un = [by_level[lvl]["ungated"]["sortino_ratio"] if lvl in by_level else np.nan for lvl in levels]
        ax_s = axes[1, col]
        ax_s.bar(x - width, sortino_un, width, label="Sin filtro", color="#7f8fa6")
        for j, mode in enumerate(GATE_MODES):
            sortino_g = [by_level[lvl]["gated"][mode]["metrics"]["sortino_ratio"] if lvl in by_level else np.nan
                         for lvl in levels]
            ax_s.bar(x + j * width, sortino_g, width, label=GATE_LABELS[mode], color=GATE_COLORS[mode])
        ax_s.axhline(0.0, color="red", linestyle="--", linewidth=1)
        ax_s.set_title(f"{instrument} -- Sortino ratio (test)", fontsize=10)
        ax_s.set_xticks(x)
        ax_s.set_xticklabels(levels, rotation=15, ha="right", fontsize=8)
        ax_s.legend(fontsize=7)
        ax_s.grid(axis="y", alpha=0.3)

    fig.suptitle("Rentabilidad fuera de muestra (test) por nivel: sin filtro vs los dos umbrales de régimen")
    fig.tight_layout()
    fig.savefig(outdir / "profitability_by_level.png", dpi=140)
    plt.close(fig)


def _plot_equity_curves(outdir, equity_curves):
    instruments = sorted(set(k[0] for k in equity_curves))
    variants = ["ungated"] + GATE_MODES
    variant_labels = {"ungated": "Sin filtro", **GATE_LABELS}
    variant_colors = {"ungated": "#7f8fa6", **GATE_COLORS}
    for instrument in instruments:
        levels = [lvl for (inst, lvl, _) in equity_curves if inst == instrument]
        levels = list(dict.fromkeys(levels))
        fig, axes = plt.subplots(1, len(levels), figsize=(6.5 * len(levels), 4.5), sharey=False)
        if len(levels) == 1:
            axes = [axes]
        for ax, level in zip(axes, levels):
            for variant in variants:
                ec = equity_curves.get((instrument, level, variant))
                if ec is not None:
                    ax.plot(ec.index, ec.values, label=variant_labels[variant], color=variant_colors[variant])
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
