# ORB clásico (sin absorción CVD): barrido de parámetros con split train/test

Split honesto por fecha: la primera mitad de los ~6 meses reales de QQQ se usa para elegir la mejor combinación de parámetros por Sortino ratio (train); la segunda mitad se evalúa SOLO con esa combinación ya elegida, sin volver a buscar parámetros (test, fuera de muestra). Esto es lo mínimo para no reportar un número inflado por sobreajuste al dataset completo.

Grid: OR=[15, 25, 30, 35, 45] min, SL=['or_opposite', 'liquidity'], TP=[1.5, 2.0, 3.0]R, filtro de tendencia=[False, True], dirección=['breakout', 'fade'] (120 combinaciones), mínimo 10 trades en train para poder elegirse. Sizing con `max_leverage=1.0` (sin margen: la posición nunca excede el equity disponible, incluso si el SL queda muy ajustado -- ver src/simple_orb.py).

## 1m

- Train: 62 días (hasta antes de 2026-06-12)
- Test: 63 días (desde 2026-06-12, fuera de muestra)

**Combo elegido en train:** `{'or_minutes': 30, 'sl_mode': 'or_opposite', 'tp_r_multiple': 2.0, 'trend_filter_enabled': False, 'direction_mode': 'fade'}`

| | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|
| train (in-sample) | 61 | 2.35 | 49.18 | 1.92 | 0.33 | -0.77 | 4.485 | 9.997 |
| test (fuera de muestra) | 61 | 0.16 | 42.62 | 1.04 | 0.145 | -0.71 | 0.305 | 0.485 |

Top 5 combos en train por Sortino:

| or_minutes | sl_mode | tp_r_multiple | trend_filter_enabled | direction_mode | num_trades | sortino_ratio | profit_factor | total_return_pct |
|---|---|---|---|---|---|---|---|---|
| 30 | or_opposite | 2.0 | False | fade | 61 | 9.997 | 1.92 | 2.35 |
| 30 | or_opposite | 1.5 | False | fade | 61 | 8.728 | 1.89 | 1.91 |
| 30 | or_opposite | 1.5 | True | fade | 32 | 7.139 | 2.1 | 1.16 |
| 30 | or_opposite | 3.0 | False | fade | 61 | 6.89 | 1.56 | 1.89 |
| 30 | or_opposite | 2.0 | True | fade | 32 | 6.168 | 1.79 | 1.11 |

## 2m

- Train: 62 días (hasta antes de 2026-06-12)
- Test: 63 días (desde 2026-06-12, fuera de muestra)

**Combo elegido en train:** `{'or_minutes': 30, 'sl_mode': 'or_opposite', 'tp_r_multiple': 1.5, 'trend_filter_enabled': False, 'direction_mode': 'fade'}`

| | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|
| train (in-sample) | 61 | 2.29 | 65.57 | 2.0 | 0.506 | -0.82 | 5.072 | 8.618 |
| test (fuera de muestra) | 61 | 1.53 | 60.66 | 1.47 | 0.393 | -0.52 | 2.488 | 4.221 |

Top 5 combos en train por Sortino:

| or_minutes | sl_mode | tp_r_multiple | trend_filter_enabled | direction_mode | num_trades | sortino_ratio | profit_factor | total_return_pct |
|---|---|---|---|---|---|---|---|---|
| 30 | or_opposite | 1.5 | False | fade | 61 | 8.618 | 2.0 | 2.29 |
| 30 | or_opposite | 2.0 | False | fade | 61 | 7.788 | 1.77 | 2.26 |
| 45 | or_opposite | 3.0 | True | fade | 32 | 6.464 | 1.7 | 1.44 |
| 35 | or_opposite | 1.5 | True | fade | 34 | 6.455 | 2.1 | 1.56 |
| 30 | or_opposite | 1.5 | True | fade | 32 | 6.019 | 2.05 | 1.31 |

## 3m

- Train: 62 días (hasta antes de 2026-06-12)
- Test: 63 días (desde 2026-06-12, fuera de muestra)

**Combo elegido en train:** `{'or_minutes': 30, 'sl_mode': 'or_opposite', 'tp_r_multiple': 2.0, 'trend_filter_enabled': False, 'direction_mode': 'fade'}`

| | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|
| train (in-sample) | 61 | 2.93 | 57.38 | 2.03 | 0.592 | -0.85 | 5.075 | 9.656 |
| test (fuera de muestra) | 61 | 1.67 | 52.46 | 1.42 | 0.459 | -0.51 | 2.494 | 4.071 |

Top 5 combos en train por Sortino:

| or_minutes | sl_mode | tp_r_multiple | trend_filter_enabled | direction_mode | num_trades | sortino_ratio | profit_factor | total_return_pct |
|---|---|---|---|---|---|---|---|---|
| 30 | or_opposite | 2.0 | False | fade | 61 | 9.656 | 2.03 | 2.93 |
| 35 | liquidity | 1.5 | True | fade | 26 | 9.134 | 2.81 | 2.34 |
| 30 | or_opposite | 1.5 | False | fade | 61 | 8.904 | 2.08 | 2.52 |
| 35 | liquidity | 3.0 | True | fade | 26 | 8.773 | 2.56 | 2.59 |
| 30 | liquidity | 3.0 | True | fade | 25 | 8.209 | 2.59 | 3.23 |

## 5m

- Train: 62 días (hasta antes de 2026-06-12)
- Test: 63 días (desde 2026-06-12, fuera de muestra)

**Combo elegido en train:** `{'or_minutes': 30, 'sl_mode': 'or_opposite', 'tp_r_multiple': 3.0, 'trend_filter_enabled': False, 'direction_mode': 'fade'}`

| | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|
| train (in-sample) | 61 | 3.87 | 45.9 | 2.0 | 0.714 | -1.47 | 4.539 | 10.093 |
| test (fuera de muestra) | 61 | 1.63 | 42.62 | 1.28 | 0.583 | -1.22 | 1.639 | 3.014 |

Top 5 combos en train por Sortino:

| or_minutes | sl_mode | tp_r_multiple | trend_filter_enabled | direction_mode | num_trades | sortino_ratio | profit_factor | total_return_pct |
|---|---|---|---|---|---|---|---|---|
| 30 | or_opposite | 3.0 | False | fade | 61 | 10.093 | 2.0 | 3.87 |
| 30 | or_opposite | 1.5 | False | fade | 61 | 8.504 | 2.13 | 2.87 |
| 30 | or_opposite | 2.0 | False | fade | 61 | 7.965 | 1.9 | 2.9 |
| 25 | liquidity | 3.0 | True | fade | 27 | 7.514 | 2.83 | 4.06 |
| 25 | liquidity | 2.0 | True | fade | 27 | 6.932 | 2.88 | 3.68 |

