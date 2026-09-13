# Barrido de OR (5/10/15/30/60 min) sobre datos REALES (NASDAQ ^IXIC)

⚠️ Historial corto por límite de Yahoo Finance en datos intradía (no del código): ~20 días para 2m/5m, ~4 días para 1m/3m. Con tan pocos días el número de trades por combinación es muy bajo (a veces 0-3) — esto es una prueba de que el motor corre bien sobre datos reales y una primera lectura direccional, **no** una estimación confiable de rentabilidad ni de Sortino/Sharpe (estadísticamente poco significativos con tan pocas muestras).

| interval | n_days | or_minutes | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| 1m | 4 | 5 | 3 | -1.72 | 33.33 | 0.28 | -0.571 | -2.38 | -8.428 | -8.021 |
| 1m | 4 | 10 | 2 | -0.45 | 50.0 | 0.6 | -0.223 | -1.13 | -2.726 | -3.139 |
| 1m | 4 | 15 | 2 | 1.01 | 50.0 | 1.9 | 0.516 | -1.13 | 3.446 | 7.284 |
| 1m | 4 | 30 | 3 | -0.4 | 66.67 | 0.65 | -0.13 | -1.13 | -2.431 | -2.753 |
| 1m | 4 | 60 | 1 | -1.12 | 0.0 | 0.0 | -1.122 | -1.12 | -9.165 | -7.937 |
| 2m | 20 | 5 | 7 | -1.95 | 57.14 | 0.42 | -0.278 | -2.09 | -3.188 | -3.487 |
| 2m | 20 | 10 | 9 | -3.01 | 55.56 | 0.32 | -0.336 | -3.12 | -4.531 | -4.75 |
| 2m | 20 | 15 | 10 | 1.0 | 60.0 | 1.22 | 0.111 | -2.08 | 0.82 | 1.745 |
| 2m | 20 | 30 | 10 | 1.1 | 60.0 | 1.24 | 0.121 | -1.88 | 0.889 | 1.876 |
| 2m | 20 | 60 | 6 | -0.24 | 16.67 | 0.81 | -0.038 | -1.08 | -0.536 | -0.749 |
| 3m | 4 | 5 | 3 | 2.25 | 66.67 | 3.14 | 0.751 | -1.05 | 7.708 | 17.066 |
| 3m | 4 | 10 | 3 | 2.25 | 66.67 | 3.14 | 0.751 | -1.05 | 7.708 | 17.066 |
| 3m | 4 | 15 | 3 | 2.25 | 66.67 | 3.14 | 0.751 | -1.05 | 7.708 | 17.066 |
| 3m | 4 | 30 | 2 | 0.27 | 50.0 | 1.24 | 0.144 | -1.13 | 1.26 | 2.014 |
| 3m | 4 | 60 | 0 | 0.0 | 0.0 | nan | nan | 0.0 | 0.0 | 0.0 |
| 5m | 20 | 5 | 5 | -3.49 | 20.0 | 0.06 | -0.706 | -3.49 | -7.102 | -6.534 |
| 5m | 20 | 10 | 5 | -3.49 | 20.0 | 0.06 | -0.706 | -3.49 | -7.102 | -6.534 |
| 5m | 20 | 15 | 4 | -2.49 | 25.0 | 0.09 | -0.627 | -2.49 | -5.774 | -5.486 |
| 5m | 20 | 30 | 3 | -0.22 | 66.67 | 0.79 | -0.072 | -1.06 | -0.626 | -0.719 |
| 5m | 20 | 60 | 1 | 0.48 | 100.0 | inf | 0.475 | 0.0 | 3.642 | 0.0 |
