# Reacción al rango de Asia durante Londres (NQ real)

Se marca el rango COMPLETO de la sesión de Asia (19:00-04:00 ET) y se busca la reacción (rompimiento de ese high/low) durante la sesión de Londres (desde que Asia cierra hasta que Londres cierra, 8h). Split honesto por fecha: primera mitad del historial de NQ como train, segunda mitad ("test") nunca usada para elegir parámetros. Sizing con `max_leverage=1.0` (sin margen).

Grid: TP=['r_multiple', 'opposite_extreme', 'poc'] (con TP_R=[1.0, 1.5, 2.0, 3.0] solo para "r_multiple"), SL=['or_opposite', 'liquidity'], dirección=['fade', 'breakout'] (24 combinaciones), mínimo 10 trades en train para poder elegirse.

## 5m

- Train: 77 días (hasta antes de 2026-06-16)
- Test: 78 días (desde 2026-06-16, fuera de muestra)

**Combo elegido en train:** `{'tp_mode': 'r_multiple', 'sl_mode': 'liquidity', 'direction_mode': 'fade', 'tp_r_multiple': 2.0}`

| | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|
| train (in-sample) | 55 | 4.27 | 36.36 | 2.71 | -0.161 | -0.47 | 3.014 | 14.472 |
| test (fuera de muestra) | 52 | 1.41 | 30.77 | 1.3 | -0.316 | -2.8 | 0.935 | 2.058 |

Todas las combinaciones en train, por Sortino:

| tp_mode | tp_r_multiple | sl_mode | direction_mode | num_trades | sortino_ratio | profit_factor | total_return_pct |
|---|---|---|---|---|---|---|---|
| r_multiple | 2.0 | liquidity | fade | 55 | 14.472 | 2.71 | 4.27 |
| r_multiple | 3.0 | liquidity | fade | 55 | 14.443 | 2.6 | 4.59 |
| r_multiple | 1.5 | liquidity | fade | 55 | 11.583 | 2.4 | 3.34 |
| r_multiple | 1.0 | liquidity | fade | 55 | 8.765 | 2.12 | 2.39 |
| opposite_extreme |  | liquidity | fade | 55 | 6.621 | 1.66 | 2.24 |
| poc |  | liquidity | fade | 55 | 5.348 | 1.52 | 1.4 |
| r_multiple | 1.5 | or_opposite | breakout | 62 | 1.923 | 1.22 | 3.26 |
| r_multiple | 2.0 | or_opposite | breakout | 62 | 1.882 | 1.21 | 3.2 |
| r_multiple | 1.0 | or_opposite | breakout | 62 | 1.284 | 1.15 | 2.14 |
| r_multiple | 3.0 | or_opposite | breakout | 62 | 1.223 | 1.13 | 2.04 |
| r_multiple | 1.0 | liquidity | breakout | 62 | 1.037 | 1.11 | 0.85 |
| opposite_extreme |  | or_opposite | breakout | 0 | 0.0 | nan | 0.0 |

## 15m

- Train: 77 días (hasta antes de 2026-06-16)
- Test: 78 días (desde 2026-06-16, fuera de muestra)

**Combo elegido en train:** `{'tp_mode': 'r_multiple', 'sl_mode': 'liquidity', 'direction_mode': 'fade', 'tp_r_multiple': 1.0}`

| | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|
| train (in-sample) | 47 | 4.57 | 57.45 | 2.68 | 0.047 | -0.8 | 3.93 | 10.044 |
| test (fuera de muestra) | 47 | 1.08 | 48.94 | 1.24 | -0.158 | -1.09 | 0.97 | 1.607 |

Todas las combinaciones en train, por Sortino:

| tp_mode | tp_r_multiple | sl_mode | direction_mode | num_trades | sortino_ratio | profit_factor | total_return_pct |
|---|---|---|---|---|---|---|---|
| r_multiple | 1.0 | liquidity | fade | 47 | 10.044 | 2.68 | 4.57 |
| r_multiple | 1.5 | liquidity | fade | 47 | 7.553 | 2.15 | 4.08 |
| r_multiple | 3.0 | liquidity | fade | 47 | 4.937 | 1.67 | 3.03 |
| r_multiple | 2.0 | liquidity | fade | 47 | 4.367 | 1.61 | 2.64 |
| poc |  | liquidity | fade | 47 | 3.987 | 1.6 | 1.94 |
| opposite_extreme |  | liquidity | fade | 47 | 2.287 | 1.29 | 1.4 |
| r_multiple | 1.5 | liquidity | breakout | 58 | 2.196 | 1.25 | 2.52 |
| r_multiple | 1.0 | or_opposite | fade | 62 | 1.938 | 1.33 | 1.0 |
| r_multiple | 1.5 | or_opposite | breakout | 62 | 1.923 | 1.22 | 3.26 |
| r_multiple | 2.0 | or_opposite | breakout | 62 | 1.882 | 1.21 | 3.2 |
| r_multiple | 1.0 | or_opposite | breakout | 62 | 1.284 | 1.15 | 2.14 |
| r_multiple | 1.0 | liquidity | breakout | 58 | 1.246 | 1.15 | 1.34 |

