#!/usr/bin/env python3
"""Grafica UN trade real del backtest (apertura NY + fade + filtro
'solo rojo' en NQ) paso a paso: rango de apertura, ruptura, entrada,
SL, TP y salida -- para ver la estrategia "en acción" sobre un ejemplo
concreto, no solo en agregados."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd

from src.data import load_csv, restrict_to_session
from src.market_regime import compute_regime
from src.simple_orb import SimpleORBConfig, run_backtest_simple

DF_PATH = str(ROOT / "data" / "databento_NQ_c_0_5m_candles.csv")
TRADE_DATE = pd.Timestamp("2026-04-27").date()

df = load_csv(DF_PATH, tz="America/New_York")
regime_full = compute_regime(df)["regime"]
cfg = SimpleORBConfig(
    direction_mode="fade", sl_mode="or_opposite", tp_mode="r_multiple", tp_r_multiple=1.5,
    sl_buffer_pct=0.03, trend_filter_enabled=False, max_leverage=1.0,
    range_source="opening_range", or_minutes=30, session_only=True, volume_filter_enabled=False,
)
trades, ec = run_backtest_simple(df, cfg, regime=regime_full, regime_mode="red_only")
t = trades[trades["date"] == TRADE_DATE].iloc[0]
print(t)

session_df = restrict_to_session(df, "09:30", "16:00")
day_df = session_df[session_df.index.date == TRADE_DATE]

entry_time = pd.Timestamp(t["entry_time"])
exit_time = pd.Timestamp(t["exit_time"])
or_end_time = day_df.index[0] + pd.Timedelta(minutes=30)

fig, ax = plt.subplots(figsize=(13, 7))

# --- velas (candlestick manual) ---
bar_width = pd.Timedelta(minutes=4)
for ts, row in day_df.iterrows():
    color = "#26a65b" if row["close"] >= row["open"] else "#c0392b"
    ax.plot([ts, ts], [row["low"], row["high"]], color=color, linewidth=1, zorder=2)
    ax.add_patch(mpatches.Rectangle(
        (mdates.date2num(ts) - bar_width.total_seconds() / 86400 / 2, min(row["open"], row["close"])),
        bar_width.total_seconds() / 86400,
        max(abs(row["close"] - row["open"]), 0.05),
        facecolor=color, edgecolor=color, zorder=3,
    ))

# --- rango de apertura (OR30) sombreado ---
ax.axvspan(day_df.index[0], or_end_time, color="#f1c40f", alpha=0.18, label="Rango de apertura (09:30-10:00)")
ax.axhline(t["or_high"], color="#8e44ad", linestyle="--", linewidth=1.3, label=f"OR-high {t['or_high']:.1f}")
ax.axhline(t["or_low"], color="#8e44ad", linestyle="--", linewidth=1.3, label=f"OR-low {t['or_low']:.1f}")

# --- niveles del trade ---
ax.axhline(t["sl"], color="#c0392b", linestyle=":", linewidth=1.6, label=f"Stop loss {t['sl']:.1f}")
ax.axhline(t["tp"], color="#27ae60", linestyle=":", linewidth=1.6, label=f"Take profit {t['tp']:.1f}")

# --- marcadores de entrada/salida ---
ax.scatter([entry_time], [t["entry_price"]], marker="v", s=220, color="#2c3e50", zorder=5,
           label=f"Entrada SHORT @ {t['entry_price']:.1f} (fade del breakout del OR-high)")
ax.scatter([exit_time], [t["exit_price"]], marker="*", s=320, color="#27ae60", zorder=5,
           label=f"Salida por TP @ {t['exit_price']:.1f}")

ax.annotate(
    "Rompe el OR-high (barrida de liquidez)\nRégimen VOLÁTIL (rojo) -> se opera el FADE: SHORT",
    xy=(entry_time, t["entry_price"]), xytext=(entry_time + pd.Timedelta(minutes=55), t["or_high"] + 22),
    fontsize=9, color="#2c3e50",
    arrowprops=dict(arrowstyle="->", color="#2c3e50"),
)
ax.annotate(
    f"TP: +{t['r_multiple']:.2f}R (${t['pnl']:.0f})",
    xy=(exit_time, t["exit_price"]), xytext=(exit_time + pd.Timedelta(minutes=25), t["exit_price"] + 2),
    fontsize=9, color="#1e8449", fontweight="bold",
    arrowprops=dict(arrowstyle="->", color="#1e8449"),
)

ax.set_title(
    f"Estrategia en acción -- US100/NQ, {TRADE_DATE} -- Fade del rango de apertura de NY (OR30), "
    f"filtrado por régimen VOLÁTIL (rojo)",
    fontsize=12,
)
ax.set_ylabel("Precio (puntos NQ)")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=day_df.index.tz))
ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=30))
plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")
ax.legend(loc="upper left", fontsize=8, framealpha=0.95)
ax.grid(alpha=0.25)
fig.tight_layout()

outpath = str(ROOT / "results" / "regime_gated_levels" / "trade_example_us100_2026-04-27.png")
fig.savefig(outpath, dpi=150)
print("guardado en", outpath)
