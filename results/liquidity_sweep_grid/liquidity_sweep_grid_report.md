# Barrido de liquidez (PDH/PDL) con objetivo en el lado opuesto y en el POC

`range_source="prev_session"`: el rompimiento se mide contra el high/low de TODA la sesión de trading anterior (no el rango de apertura de hoy). `tp_mode="opposite_extreme"` apunta al lado del rango anterior que NO se rompió; `tp_mode="poc"` apunta al Punto de Control (nivel de más volumen) de la sesión anterior. Mismo split honesto train/test por fecha que la variante fade original: la primera mitad de los ~6 meses reales de QQQ elige la mejor combinación por Sortino (train); la segunda mitad, nunca vista, evalúa esa combinación ya fija (test). Sizing con `max_leverage=1.0` (sin margen). Se agregó `tp_mode="r_multiple"` (el mismo objetivo de múltiplo de R fijo que la variante OR30 validada) para aislar si el problema es el objetivo (lado opuesto/POC) o el rango de referencia en sí (PDH/PDL de la sesión anterior, en vez del rango de apertura).

Grid: TP=['opposite_extreme', 'poc', 'r_multiple'] (con TP_R=[1.0, 1.5, 2.0, 3.0] solo para "r_multiple"), SL=['or_opposite', 'liquidity'], dirección=['fade', 'breakout'], filtro de tendencia=[False, True] (48 combinaciones), mínimo 10 trades en train para poder elegirse.

## 1m

- Train: 62 días (hasta antes de 2026-06-12)
- Test: 63 días (desde 2026-06-12, fuera de muestra)

**Combo elegido en train:** `{'tp_mode': 'r_multiple', 'sl_mode': 'liquidity', 'direction_mode': 'breakout', 'trend_filter_enabled': False, 'tp_r_multiple': 1.5}`

| | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|
| train (in-sample) | 58 | 7.02 | 46.55 | 1.88 | 0.109 | -1.01 | 3.855 | 8.343 |
| test (fuera de muestra) | 57 | -3.72 | 35.09 | 0.7 | -0.314 | -4.76 | -2.137 | -2.853 |

Todas las combinaciones en train, por Sortino:

| tp_mode | tp_r_multiple | sl_mode | direction_mode | trend_filter_enabled | num_trades | sortino_ratio | profit_factor | total_return_pct |
|---|---|---|---|---|---|---|---|---|
| r_multiple | 1.5 | liquidity | breakout | False | 58 | 8.343 | 1.88 | 7.02 |
| r_multiple | 3.0 | liquidity | breakout | False | 58 | 7.65 | 1.71 | 6.98 |
| r_multiple | 1.0 | or_opposite | breakout | False | 58 | 6.65 | 1.92 | 7.84 |
| r_multiple | 1.0 | liquidity | breakout | False | 58 | 6.393 | 1.71 | 5.18 |
| r_multiple | 1.5 | or_opposite | breakout | False | 58 | 6.072 | 1.81 | 7.42 |
| r_multiple | 2.0 | liquidity | breakout | False | 58 | 5.701 | 1.53 | 5.12 |
| r_multiple | 2.0 | or_opposite | breakout | False | 58 | 5.25 | 1.7 | 6.38 |
| r_multiple | 3.0 | or_opposite | breakout | False | 58 | 5.25 | 1.7 | 6.38 |
| r_multiple | 1.5 | liquidity | breakout | True | 35 | 4.303 | 1.53 | 2.94 |
| r_multiple | 1.0 | or_opposite | breakout | True | 35 | 3.606 | 1.61 | 2.77 |
| r_multiple | 1.5 | or_opposite | breakout | True | 35 | 3.58 | 1.61 | 2.75 |
| r_multiple | 2.0 | or_opposite | breakout | True | 35 | 3.58 | 1.61 | 2.75 |

## 2m

- Train: 62 días (hasta antes de 2026-06-12)
- Test: 63 días (desde 2026-06-12, fuera de muestra)

**Combo elegido en train:** `{'tp_mode': 'r_multiple', 'sl_mode': 'or_opposite', 'direction_mode': 'breakout', 'trend_filter_enabled': False, 'tp_r_multiple': 1.0}`

| | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|
| train (in-sample) | 58 | 7.84 | 63.79 | 1.92 | 0.132 | -1.88 | 4.008 | 6.65 |
| test (fuera de muestra) | 57 | 1.75 | 52.63 | 1.19 | 0.041 | -2.21 | 1.063 | 1.564 |

Todas las combinaciones en train, por Sortino:

| tp_mode | tp_r_multiple | sl_mode | direction_mode | trend_filter_enabled | num_trades | sortino_ratio | profit_factor | total_return_pct |
|---|---|---|---|---|---|---|---|---|
| r_multiple | 1.0 | or_opposite | breakout | False | 58 | 6.65 | 1.92 | 7.84 |
| r_multiple | 3.0 | liquidity | breakout | False | 58 | 6.1 | 1.62 | 6.91 |
| r_multiple | 1.5 | or_opposite | breakout | False | 58 | 6.072 | 1.81 | 7.42 |
| r_multiple | 1.5 | liquidity | breakout | False | 58 | 5.614 | 1.63 | 6.07 |
| r_multiple | 2.0 | liquidity | breakout | False | 58 | 5.368 | 1.56 | 6.01 |
| r_multiple | 2.0 | or_opposite | breakout | False | 58 | 5.25 | 1.7 | 6.38 |
| r_multiple | 3.0 | or_opposite | breakout | False | 58 | 5.25 | 1.7 | 6.38 |
| r_multiple | 1.0 | liquidity | breakout | False | 58 | 4.568 | 1.56 | 4.71 |
| r_multiple | 1.0 | or_opposite | breakout | True | 35 | 3.606 | 1.61 | 2.77 |
| r_multiple | 1.5 | or_opposite | breakout | True | 35 | 3.58 | 1.61 | 2.75 |
| r_multiple | 2.0 | or_opposite | breakout | True | 35 | 3.58 | 1.61 | 2.75 |
| r_multiple | 3.0 | or_opposite | breakout | True | 35 | 3.58 | 1.61 | 2.75 |

## 3m

- Train: 62 días (hasta antes de 2026-06-12)
- Test: 63 días (desde 2026-06-12, fuera de muestra)

**Combo elegido en train:** `{'tp_mode': 'r_multiple', 'sl_mode': 'or_opposite', 'direction_mode': 'breakout', 'trend_filter_enabled': False, 'tp_r_multiple': 1.0}`

| | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|
| train (in-sample) | 58 | 7.84 | 63.79 | 1.92 | 0.132 | -1.88 | 4.008 | 6.65 |
| test (fuera de muestra) | 57 | 1.75 | 52.63 | 1.19 | 0.041 | -2.21 | 1.063 | 1.564 |

Todas las combinaciones en train, por Sortino:

| tp_mode | tp_r_multiple | sl_mode | direction_mode | trend_filter_enabled | num_trades | sortino_ratio | profit_factor | total_return_pct |
|---|---|---|---|---|---|---|---|---|
| r_multiple | 1.0 | or_opposite | breakout | False | 58 | 6.65 | 1.92 | 7.84 |
| r_multiple | 1.0 | liquidity | breakout | False | 58 | 6.318 | 1.76 | 6.65 |
| r_multiple | 1.5 | or_opposite | breakout | False | 58 | 6.072 | 1.81 | 7.42 |
| r_multiple | 3.0 | liquidity | breakout | False | 58 | 5.257 | 1.54 | 5.97 |
| r_multiple | 2.0 | or_opposite | breakout | False | 58 | 5.25 | 1.7 | 6.38 |
| r_multiple | 3.0 | or_opposite | breakout | False | 58 | 5.25 | 1.7 | 6.38 |
| r_multiple | 1.5 | liquidity | breakout | False | 58 | 4.87 | 1.53 | 5.39 |
| r_multiple | 2.0 | liquidity | breakout | False | 58 | 4.189 | 1.43 | 4.72 |
| r_multiple | 1.0 | or_opposite | breakout | True | 35 | 3.606 | 1.61 | 2.77 |
| r_multiple | 1.5 | or_opposite | breakout | True | 35 | 3.58 | 1.61 | 2.75 |
| r_multiple | 2.0 | or_opposite | breakout | True | 35 | 3.58 | 1.61 | 2.75 |
| r_multiple | 3.0 | or_opposite | breakout | True | 35 | 3.58 | 1.61 | 2.75 |

## 5m

- Train: 62 días (hasta antes de 2026-06-12)
- Test: 63 días (desde 2026-06-12, fuera de muestra)

**Combo elegido en train:** `{'tp_mode': 'r_multiple', 'sl_mode': 'liquidity', 'direction_mode': 'breakout', 'trend_filter_enabled': False, 'tp_r_multiple': 1.0}`

| | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|
| train (in-sample) | 57 | 10.27 | 59.65 | 2.24 | 0.13 | -1.16 | 5.169 | 9.802 |
| test (fuera de muestra) | 57 | -0.76 | 43.86 | 0.94 | -0.101 | -3.56 | -0.36 | -0.504 |

Todas las combinaciones en train, por Sortino:

| tp_mode | tp_r_multiple | sl_mode | direction_mode | trend_filter_enabled | num_trades | sortino_ratio | profit_factor | total_return_pct |
|---|---|---|---|---|---|---|---|---|
| r_multiple | 1.0 | liquidity | breakout | False | 57 | 9.802 | 2.24 | 10.27 |
| r_multiple | 3.0 | liquidity | breakout | False | 57 | 9.792 | 2.1 | 11.0 |
| r_multiple | 2.0 | liquidity | breakout | False | 57 | 9.365 | 2.05 | 10.49 |
| r_multiple | 1.5 | liquidity | breakout | False | 57 | 8.952 | 2.01 | 10.01 |
| r_multiple | 3.0 | liquidity | breakout | True | 34 | 6.861 | 1.97 | 5.21 |
| r_multiple | 2.0 | liquidity | breakout | True | 34 | 6.666 | 1.94 | 5.06 |
| r_multiple | 1.0 | or_opposite | breakout | False | 58 | 6.65 | 1.92 | 7.84 |
| r_multiple | 1.5 | or_opposite | breakout | False | 58 | 6.072 | 1.81 | 7.42 |
| r_multiple | 1.0 | liquidity | breakout | True | 34 | 6.07 | 1.91 | 4.47 |
| r_multiple | 1.5 | liquidity | breakout | True | 34 | 5.897 | 1.84 | 4.46 |
| r_multiple | 2.0 | or_opposite | breakout | False | 58 | 5.25 | 1.7 | 6.38 |
| r_multiple | 3.0 | or_opposite | breakout | False | 58 | 5.25 | 1.7 | 6.38 |

