# Barrido del rango de apertura (OR): 15 / 30 / 60 min

Mismo motor (filtro de volumen + absorción CVD + SL/TP por swings), solo cambia cuántos minutos de la apertura de NY se usan para marcar el high/low inicial. Sobre los 3 datasets sintéticos A/B/C.

| dataset | or_minutes | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|---|
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
