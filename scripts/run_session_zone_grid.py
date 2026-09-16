#!/usr/bin/env python3
"""Corre la MISMA receta ya validada (fade + SL en la mecha real + TP de
1.5R fijo, ver src/simple_orb.py y el README) sobre las 6 "zonas de
valor" de 30 minutos definidas en src/session_zone.py: los primeros y los
últimos 30 minutos de las sesiones de Asia, Londres y Nueva York.

Usa datos de NQ (futuro E-mini Nasdaq-100, CME Globex vía Databento
GLBX.MDP3, ~24h) -- QQQ no sirve para esto porque no cotiza en las
sesiones de Asia/Londres. Mismo split honesto train/test por fecha que el
resto del proyecto (primera mitad del historial para referencia, segunda
mitad -- "test" -- nunca usada para elegir nada, mismos parámetros fijos
en las 6 zonas para no maquillar el resultado).

Uso:
    python scripts/run_session_zone_grid.py                  # 5m y 15m
    python scripts/run_session_zone_grid.py --interval 5m
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import load_csv  # noqa: E402
from src.metrics import compute_metrics  # noqa: E402
from src.session_zone import SessionZoneConfig, ZONES, run_backtest_zone  # noqa: E402

SOURCES = {
    "5m": "data/databento_NQ_c_0_5m_candles.csv",
    "15m": "data/databento_NQ_c_0_15m_candles.csv",
}

MAX_LEVERAGE = 1.0  # sin margen, misma convención que la variante OR30 validada


def _split_train_test(df):
    dates = sorted(set(df.index.date))
    split_date = dates[len(dates) // 2]
    train = df[df.index.date < split_date]
    test = df[df.index.date >= split_date]
    return train, test, split_date


def run_for_interval(label: str, path: str):
    df = load_csv(path, tz="America/New_York")
    train_df, test_df, split_date = _split_train_test(df)
    n_train_days = len(set(train_df.index.date))
    n_test_days = len(set(test_df.index.date))
    print(f"\n=== {label}: {n_train_days} días train (< {split_date}), "
          f"{n_test_days} días test (>= {split_date}) ===")

    rows = []
    for zone_name, zone_params in ZONES.items():
        cfg = SessionZoneConfig(max_leverage=MAX_LEVERAGE, **zone_params)

        train_trades, train_ec = run_backtest_zone(train_df, cfg)
        train_metrics = compute_metrics(train_trades, train_ec)

        test_trades, test_ec = run_backtest_zone(test_df, cfg)
        test_metrics = compute_metrics(test_trades, test_ec)

        print(f"  {zone_name:16} train: n={train_metrics['num_trades']:>3} "
              f"pf={train_metrics['profit_factor']:>5} sortino={train_metrics['sortino_ratio']:>7}  |  "
              f"test: n={test_metrics['num_trades']:>3} pf={test_metrics['profit_factor']:>5} "
              f"sortino={test_metrics['sortino_ratio']:>7}")

        rows.append({
            "zone": zone_name, "zone_params": zone_params,
            "train": train_metrics, "test": test_metrics,
        })

    return {
        "interval": label, "split_date": str(split_date),
        "n_train_days": n_train_days, "n_test_days": n_test_days, "zones": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", default=None, choices=list(SOURCES.keys()),
                         help="Un solo intervalo; default: corre 5m y 15m")
    parser.add_argument("--outdir", default="results/session_zone_grid")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    intervals = [args.interval] if args.interval else list(SOURCES.keys())
    results = {}
    for label in intervals:
        path = SOURCES[label]
        if not Path(path).exists():
            print(f"[{label}] archivo no encontrado, se omite: {path}")
            continue
        results[label] = run_for_interval(label, path)

    with open(outdir / "session_zone_grid_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    md_path = outdir / "session_zone_grid_report.md"
    with open(md_path, "w") as f:
        f.write("# Zonas de valor de 30 min (Asia/Londres/NY, primeros y últimos) sobre NQ real\n\n")
        f.write(
            "Misma receta ya validada (fade + SL en la mecha real + TP de 1.5R fijo, sin filtro "
            "de tendencia ni de volumen, `max_leverage=1.0` sin margen) aplicada, SIN "
            "re-optimizar nada, a 6 zonas horarias de 30 min distintas. Split honesto por fecha: "
            "primera mitad del historial de NQ (~180 días) como referencia, segunda mitad "
            "(\"test\") nunca usada para elegir parámetros.\n\n"
        )
        cols = ["num_trades", "win_rate_pct", "profit_factor", "sortino_ratio", "total_return_pct", "max_drawdown_pct"]
        for label, r in results.items():
            f.write(f"## {label}\n\n")
            f.write(f"- Train: {r['n_train_days']} días (hasta antes de {r['split_date']})\n")
            f.write(f"- Test: {r['n_test_days']} días (desde {r['split_date']}, fuera de muestra)\n\n")
            f.write("| Zona | | " + " | ".join(cols) + " |\n")
            f.write("|---|---|" + "---|" * len(cols) + "\n")
            for row in r["zones"]:
                f.write(f"| {row['zone']} | train | " + " | ".join(str(row["train"][c]) for c in cols) + " |\n")
                f.write(f"| {row['zone']} | **test** | " + " | ".join(str(row["test"][c]) for c in cols) + " |\n")
            f.write("\n")

    print(f"\nReporte guardado en {outdir}/: session_zone_grid_report.md, session_zone_grid_results.json")


if __name__ == "__main__":
    main()
