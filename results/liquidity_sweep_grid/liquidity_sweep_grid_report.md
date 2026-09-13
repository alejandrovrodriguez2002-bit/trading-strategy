# Barrido de liquidez (PDH/PDL) con objetivo en el lado opuesto y en el POC

`range_source="prev_session"`: el rompimiento se mide contra el high/low de TODA la sesión de trading anterior (no el rango de apertura de hoy). `tp_mode="opposite_extreme"` apunta al lado del rango anterior que NO se rompió; `tp_mode="poc"` apunta al Punto de Control (nivel de más volumen) de la sesión anterior. Mismo split honesto train/test por fecha que la variante fade original: la primera mitad de los ~6 meses reales de QQQ elige la mejor combinación por Sortino (train); la segunda mitad, nunca vista, evalúa esa combinación ya fija (test). Sizing con `max_leverage=1.0` (sin margen).

Grid: TP=['opposite_extreme', 'poc'], SL=['or_opposite', 'liquidity'], dirección=['fade', 'breakout'], filtro de tendencia=[False, True] (16 combinaciones), mínimo 10 trades en train para poder elegirse.

## 1m

- Train: 62 días (hasta antes de 2026-06-12)
- Test: 63 días (desde 2026-06-12, fuera de muestra)

**Combo elegido en train:** `{'tp_mode': 'opposite_extreme', 'sl_mode': 'liquidity', 'direction_mode': 'fade', 'trend_filter_enabled': True}`

| | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|
| train (in-sample) | 17 | -0.64 | 11.76 | 0.73 | -0.86 | -1.2 | -0.742 | -1.324 |
| test (fuera de muestra) | 13 | -1.94 | 15.38 | 0.36 | -0.658 | -2.09 | -2.639 | -3.242 |

Todas las combinaciones en train, por Sortino:

| tp_mode | sl_mode | direction_mode | trend_filter_enabled | num_trades | sortino_ratio | profit_factor | total_return_pct |
|---|---|---|---|---|---|---|---|
| opposite_extreme | or_opposite | breakout | False | 0 | 0.0 | nan | 0.0 |
| opposite_extreme | or_opposite | breakout | True | 0 | 0.0 | nan | 0.0 |
| opposite_extreme | liquidity | breakout | False | 0 | 0.0 | nan | 0.0 |
| opposite_extreme | liquidity | breakout | True | 0 | 0.0 | nan | 0.0 |
| poc | or_opposite | breakout | False | 0 | 0.0 | nan | 0.0 |
| poc | or_opposite | breakout | True | 0 | 0.0 | nan | 0.0 |
| poc | liquidity | breakout | False | 0 | 0.0 | nan | 0.0 |
| poc | liquidity | breakout | True | 0 | 0.0 | nan | 0.0 |

## 2m

- Train: 62 días (hasta antes de 2026-06-12)
- Test: 63 días (desde 2026-06-12, fuera de muestra)

**Combo elegido en train:** `{'tp_mode': 'opposite_extreme', 'sl_mode': 'liquidity', 'direction_mode': 'fade', 'trend_filter_enabled': True}`

| | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|
| train (in-sample) | 16 | 0.09 | 18.75 | 1.04 | -0.529 | -1.24 | 0.108 | 0.243 |
| test (fuera de muestra) | 13 | 0.47 | 30.77 | 1.24 | -0.089 | -0.78 | 0.549 | 1.162 |

Todas las combinaciones en train, por Sortino:

| tp_mode | sl_mode | direction_mode | trend_filter_enabled | num_trades | sortino_ratio | profit_factor | total_return_pct |
|---|---|---|---|---|---|---|---|
| opposite_extreme | liquidity | fade | True | 16 | 0.243 | 1.04 | 0.09 |
| opposite_extreme | or_opposite | breakout | False | 0 | 0.0 | nan | 0.0 |
| opposite_extreme | or_opposite | breakout | True | 0 | 0.0 | nan | 0.0 |
| opposite_extreme | liquidity | breakout | False | 0 | 0.0 | nan | 0.0 |
| opposite_extreme | liquidity | breakout | True | 0 | 0.0 | nan | 0.0 |
| poc | or_opposite | breakout | False | 0 | 0.0 | nan | 0.0 |
| poc | or_opposite | breakout | True | 0 | 0.0 | nan | 0.0 |
| poc | liquidity | breakout | False | 0 | 0.0 | nan | 0.0 |

## 3m

- Train: 62 días (hasta antes de 2026-06-12)
- Test: 63 días (desde 2026-06-12, fuera de muestra)

**Combo elegido en train:** `{'tp_mode': 'opposite_extreme', 'sl_mode': 'liquidity', 'direction_mode': 'fade', 'trend_filter_enabled': True}`

| | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|
| train (in-sample) | 16 | -2.08 | 6.25 | 0.21 | -0.922 | -2.08 | -3.558 | -3.91 |
| test (fuera de muestra) | 11 | 0.89 | 36.36 | 1.58 | -0.195 | -0.66 | 1.036 | 2.331 |

Todas las combinaciones en train, por Sortino:

| tp_mode | sl_mode | direction_mode | trend_filter_enabled | num_trades | sortino_ratio | profit_factor | total_return_pct |
|---|---|---|---|---|---|---|---|
| opposite_extreme | or_opposite | breakout | False | 0 | 0.0 | nan | 0.0 |
| opposite_extreme | or_opposite | breakout | True | 0 | 0.0 | nan | 0.0 |
| opposite_extreme | liquidity | breakout | False | 0 | 0.0 | nan | 0.0 |
| opposite_extreme | liquidity | breakout | True | 0 | 0.0 | nan | 0.0 |
| poc | or_opposite | breakout | False | 0 | 0.0 | nan | 0.0 |
| poc | or_opposite | breakout | True | 0 | 0.0 | nan | 0.0 |
| poc | liquidity | breakout | False | 0 | 0.0 | nan | 0.0 |
| poc | liquidity | breakout | True | 0 | 0.0 | nan | 0.0 |

## 5m

- Train: 62 días (hasta antes de 2026-06-12)
- Test: 63 días (desde 2026-06-12, fuera de muestra)

**Combo elegido en train:** `{'tp_mode': 'opposite_extreme', 'sl_mode': 'liquidity', 'direction_mode': 'fade', 'trend_filter_enabled': True}`

| | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|
| train (in-sample) | 17 | -1.75 | 11.76 | 0.33 | -0.779 | -1.75 | -2.897 | -3.29 |
| test (fuera de muestra) | 11 | -1.3 | 27.27 | 0.47 | -0.536 | -1.5 | -1.799 | -2.251 |

Todas las combinaciones en train, por Sortino:

| tp_mode | sl_mode | direction_mode | trend_filter_enabled | num_trades | sortino_ratio | profit_factor | total_return_pct |
|---|---|---|---|---|---|---|---|
| opposite_extreme | or_opposite | breakout | False | 0 | 0.0 | nan | 0.0 |
| opposite_extreme | or_opposite | breakout | True | 0 | 0.0 | nan | 0.0 |
| opposite_extreme | liquidity | breakout | False | 0 | 0.0 | nan | 0.0 |
| opposite_extreme | liquidity | breakout | True | 0 | 0.0 | nan | 0.0 |
| poc | or_opposite | breakout | False | 0 | 0.0 | nan | 0.0 |
| poc | or_opposite | breakout | True | 0 | 0.0 | nan | 0.0 |
| poc | liquidity | breakout | False | 0 | 0.0 | nan | 0.0 |
| poc | liquidity | breakout | True | 0 | 0.0 | nan | 0.0 |

