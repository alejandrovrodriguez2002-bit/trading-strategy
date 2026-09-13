# Barrido del rango de apertura (OR): 5/10/15/30/60 min

Mismo motor (filtro de volumen + absorción CVD + SL/TP por swings), solo cambia cuántos minutos de la apertura de NY se usan para marcar el high/low inicial. Sobre los 3 datasets sintéticos A/B/C.

| dataset | or_minutes | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|---|
| A — Tradicional (GBM+GARCH) | 5 | 17 | -5.24 | 29.41 | 0.32 | -0.314 | -6.35 | -2.445 | -2.757 |
| B — SOC/multifractal | 5 | 24 | -0.96 | 45.83 | 0.91 | -0.033 | -5.45 | -0.19 | -0.355 |
| C — Regime-switching | 5 | 18 | 8.19 | 72.22 | 3.15 | 0.447 | -2.3 | 1.899 | 5.633 |
| A — Tradicional (GBM+GARCH) | 10 | 25 | -6.54 | 32.0 | 0.4 | -0.268 | -7.06 | -2.507 | -2.94 |
| B — SOC/multifractal | 10 | 29 | 0.88 | 44.83 | 1.08 | 0.037 | -4.38 | 0.238 | 0.465 |
| C — Regime-switching | 10 | 28 | 6.21 | 67.86 | 2.0 | 0.219 | -3.35 | 1.783 | 3.463 |
| A — Tradicional (GBM+GARCH) | 15 | 29 | -4.5 | 37.93 | 0.58 | -0.156 | -5.03 | -1.629 | -2.054 |
| B — SOC/multifractal | 15 | 28 | -2.93 | 35.71 | 0.76 | -0.1 | -5.42 | -0.631 | -1.147 |
| C — Regime-switching | 15 | 30 | 3.96 | 63.33 | 1.44 | 0.134 | -4.0 | 1.078 | 1.814 |
| A — Tradicional (GBM+GARCH) | 30 | 29 | -3.03 | 44.83 | 0.68 | -0.104 | -4.48 | -1.149 | -1.471 |
| B — SOC/multifractal | 30 | 21 | -9.2 | 28.57 | 0.18 | -0.457 | -9.32 | -3.858 | -3.922 |
| C — Regime-switching | 30 | 34 | 0.97 | 55.88 | 1.08 | 0.033 | -4.29 | 0.28 | 0.432 |
| A — Tradicional (GBM+GARCH) | 60 | 13 | -3.7 | 23.08 | 0.44 | -0.285 | -6.32 | -1.39 | -2.135 |
| B — SOC/multifractal | 60 | 10 | -5.71 | 10.0 | 0.14 | -0.584 | -5.71 | -3.003 | -3.144 |
| C — Regime-switching | 60 | 10 | 0.18 | 50.0 | 1.08 | 0.019 | -1.54 | 0.144 | 0.194 |

**Nota**: precios SINTÉTICOS — sirve para ver sensibilidad al parámetro `or_minutes`, no como estimación de rentabilidad real.
