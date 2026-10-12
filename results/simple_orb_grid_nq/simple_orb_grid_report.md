# ORB clásico (sin absorción CVD): barrido de parámetros con split train/test -- NQ (futuro CME, usado como PROXY de US100 -- ver docstring del script; US100 no cotiza en ninguna bolsa real, no hay datos de Databento para ese ticker exacto)

Instrumento: NQ (futuro CME, usado como PROXY de US100 -- ver docstring del script; US100 no cotiza en ninguna bolsa real, no hay datos de Databento para ese ticker exacto).

Split honesto por fecha: la primera mitad del historial real se usa para elegir la mejor combinación de parámetros por Sortino ratio (train); la segunda mitad se evalúa SOLO con esa combinación ya elegida, sin volver a buscar parámetros (test, fuera de muestra). Esto es lo mínimo para no reportar un número inflado por sobreajuste al dataset completo.

Grid: OR=[15, 25, 30, 35, 45] min, SL=['or_opposite', 'liquidity'], TP=[1.5, 2.0, 3.0]R, filtro de tendencia=[False, True], dirección=['breakout', 'fade'] (120 combinaciones), mínimo 10 trades en train para poder elegirse. Sizing con `max_leverage=1.0` (sin margen: la posición nunca excede el equity disponible, incluso si el SL queda muy ajustado -- ver src/simple_orb.py).

## 1m

- Train: 77 días (hasta antes de 2026-06-16)
- Test: 78 días (desde 2026-06-16, fuera de muestra)

**Combo elegido en train:** `{'or_minutes': 25, 'sl_mode': 'liquidity', 'tp_r_multiple': 1.5, 'trend_filter_enabled': True, 'direction_mode': 'fade'}`

| | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|
| train (in-sample) | 23 | 1.84 | 56.52 | 3.83 | 0.241 | -0.27 | 3.908 | 16.119 |
| test (fuera de muestra) | 23 | -0.2 | 39.13 | 0.93 | -0.256 | -1.64 | -0.284 | -0.411 |

Top 5 combos en train por Sortino:

| or_minutes | sl_mode | tp_r_multiple | trend_filter_enabled | direction_mode | num_trades | sortino_ratio | profit_factor | total_return_pct |
|---|---|---|---|---|---|---|---|---|
| 25 | liquidity | 1.5 | True | fade | 23 | 16.119 | 3.83 | 1.84 |
| 25 | liquidity | 1.5 | False | fade | 40 | 11.516 | 2.56 | 2.17 |
| 25 | liquidity | 2.0 | True | fade | 23 | 10.642 | 2.79 | 1.78 |
| 30 | or_opposite | 2.0 | False | fade | 59 | 9.586 | 1.9 | 2.26 |
| 25 | liquidity | 2.0 | False | fade | 40 | 9.371 | 2.17 | 2.16 |

## 2m

- Train: 77 días (hasta antes de 2026-06-16)
- Test: 78 días (desde 2026-06-16, fuera de muestra)

**Combo elegido en train:** `{'or_minutes': 25, 'sl_mode': 'liquidity', 'tp_r_multiple': 1.5, 'trend_filter_enabled': True, 'direction_mode': 'fade'}`

| | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|
| train (in-sample) | 21 | 2.86 | 52.38 | 6.28 | 0.075 | -0.34 | 3.393 | 30.453 |
| test (fuera de muestra) | 23 | -0.09 | 47.83 | 0.97 | -0.055 | -2.38 | -0.078 | -0.109 |

Top 5 combos en train por Sortino:

| or_minutes | sl_mode | tp_r_multiple | trend_filter_enabled | direction_mode | num_trades | sortino_ratio | profit_factor | total_return_pct |
|---|---|---|---|---|---|---|---|---|
| 25 | liquidity | 1.5 | True | fade | 21 | 30.453 | 6.28 | 2.86 |
| 25 | liquidity | 3.0 | True | fade | 21 | 29.39 | 6.19 | 3.69 |
| 25 | liquidity | 2.0 | True | fade | 21 | 22.756 | 5.01 | 2.85 |
| 30 | or_opposite | 2.0 | False | fade | 59 | 8.024 | 1.82 | 2.29 |
| 25 | liquidity | 1.5 | False | fade | 40 | 6.977 | 2.25 | 3.02 |

## 3m

- Train: 77 días (hasta antes de 2026-06-16)
- Test: 78 días (desde 2026-06-16, fuera de muestra)

**Combo elegido en train:** `{'or_minutes': 30, 'sl_mode': 'or_opposite', 'tp_r_multiple': 2.0, 'trend_filter_enabled': False, 'direction_mode': 'fade'}`

| | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|
| train (in-sample) | 59 | 2.73 | 55.93 | 1.98 | 0.549 | -0.75 | 4.838 | 9.201 |
| test (fuera de muestra) | 59 | 0.94 | 50.85 | 1.23 | 0.411 | -0.56 | 1.447 | 2.249 |

Top 5 combos en train por Sortino:

| or_minutes | sl_mode | tp_r_multiple | trend_filter_enabled | direction_mode | num_trades | sortino_ratio | profit_factor | total_return_pct |
|---|---|---|---|---|---|---|---|---|
| 30 | or_opposite | 2.0 | False | fade | 59 | 9.201 | 1.98 | 2.73 |
| 30 | or_opposite | 1.5 | False | fade | 59 | 7.166 | 1.84 | 2.04 |
| 30 | liquidity | 3.0 | True | fade | 20 | 6.425 | 2.54 | 2.44 |
| 30 | or_opposite | 3.0 | False | fade | 59 | 6.406 | 1.57 | 2.13 |
| 45 | or_opposite | 3.0 | True | breakout | 32 | 5.057 | 1.82 | 5.08 |

## 5m

- Train: 77 días (hasta antes de 2026-06-16)
- Test: 78 días (desde 2026-06-16, fuera de muestra)

**Combo elegido en train:** `{'or_minutes': 35, 'sl_mode': 'liquidity', 'tp_r_multiple': 3.0, 'trend_filter_enabled': True, 'direction_mode': 'fade'}`

| | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|
| train (in-sample) | 24 | 3.56 | 54.17 | 4.77 | 0.468 | -0.47 | 3.506 | 18.883 |
| test (fuera de muestra) | 23 | 1.67 | 43.48 | 1.9 | -0.079 | -1.39 | 2.169 | 5.037 |

Top 5 combos en train por Sortino:

| or_minutes | sl_mode | tp_r_multiple | trend_filter_enabled | direction_mode | num_trades | sortino_ratio | profit_factor | total_return_pct |
|---|---|---|---|---|---|---|---|---|
| 35 | liquidity | 3.0 | True | fade | 24 | 18.883 | 4.77 | 3.56 |
| 30 | liquidity | 3.0 | True | fade | 22 | 14.731 | 4.91 | 4.41 |
| 35 | liquidity | 2.0 | True | fade | 24 | 14.237 | 3.86 | 2.67 |
| 25 | liquidity | 3.0 | True | fade | 23 | 13.062 | 3.91 | 4.33 |
| 35 | liquidity | 1.5 | True | fade | 24 | 10.68 | 3.15 | 2.0 |

