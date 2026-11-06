# Filtro de régimen (Market Regime v7) por nivel -- dos umbrales

Misma receta fade ya validada (SL en la mecha real, TP=1.5R fijo, sin filtros de tendencia/volumen, `max_leverage=1.0`) aplicada a 3 niveles de referencia (apertura OR30, PDH/PDL, vela de 4h), con y sin el filtro de régimen (`Market Regime v7` portado a Python), en dos umbrales: **solo verde** (régimen == +1 exacto) y **no rojo** (régimen != -1, permite verde o neutral). Split honesto train/test por fecha.

## QQQ -- apertura (OR30) (train)

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 60 | 66.67 | 1.5 | 4.088 | 2.07 | -1.12 |
| Solo verde (retiene 13.3%) | 8 | 75.0 | 2.75 | 4.912 | 0.63 | -0.21 |
| No rojo (verde+neutral) (retiene 75.0%) | 45 | 66.67 | 1.84 | 5.903 | 2.16 | -0.74 |

## QQQ -- apertura (OR30) (test)

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 61 | 59.02 | 1.2 | 1.876 | 0.79 | -1.62 |
| Solo verde (retiene 18.0%) | 11 | 63.64 | 1.04 | 0.178 | 0.03 | -0.47 |
| No rojo (verde+neutral) (retiene 73.8%) | 45 | 55.56 | 1.06 | 0.486 | 0.17 | -1.7 |

## QQQ -- día anterior (PDH/PDL) (train)

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 56 | 48.21 | 0.7 | -2.979 | -2.35 | -2.84 |
| Solo verde (retiene 16.1%) | 9 | 44.44 | 0.44 | -2.216 | -0.71 | -0.95 |
| No rojo (verde+neutral) (retiene 75.0%) | 42 | 42.86 | 0.46 | -4.993 | -3.68 | -4.18 |

## QQQ -- día anterior (PDH/PDL) (test)

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 54 | 51.85 | 0.5 | -4.736 | -3.52 | -3.67 |
| Solo verde (retiene 18.5%) | 10 | 70.0 | 1.24 | 0.825 | 0.14 | -0.51 |
| No rojo (verde+neutral) (retiene 77.8%) | 42 | 52.38 | 0.54 | -3.849 | -2.4 | -2.53 |

## QQQ -- 4 horas (train)

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 107 | 54.21 | 0.92 | -1.016 | -0.94 | -2.65 |
| Solo verde (retiene 18.7%) | 20 | 45.0 | 0.36 | -3.19 | -1.49 | -1.56 |
| No rojo (verde+neutral) (retiene 79.4%) | 85 | 50.59 | 0.62 | -4.412 | -3.66 | -4.23 |

## QQQ -- 4 horas (test)

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 95 | 50.53 | 0.65 | -4.169 | -3.46 | -3.63 |
| Solo verde (retiene 18.9%) | 18 | 66.67 | 1.76 | 4.79 | 0.61 | -0.3 |
| No rojo (verde+neutral) (retiene 80.0%) | 76 | 50.0 | 0.69 | -3.356 | -2.33 | -2.54 |

## US100 (proxy NQ) -- apertura (OR30) (train)

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 60 | 65.0 | 1.66 | 5.462 | 1.9 | -0.7 |
| Solo verde (retiene 5.0%) | 3 | 0.0 | 0.0 | -3.364 | -0.45 | -0.45 |
| No rojo (verde+neutral) (retiene 46.7%) | 28 | 60.71 | 1.2 | 1.25 | 0.33 | -0.95 |

## US100 (proxy NQ) -- apertura (OR30) (test)

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 62 | 64.52 | 1.43 | 3.622 | 1.81 | -1.12 |
| Solo verde (retiene 6.5%) | 4 | 75.0 | 1.55 | 1.103 | 0.13 | -0.24 |
| No rojo (verde+neutral) (retiene 50.0%) | 31 | 58.06 | 1.0 | -0.007 | -0.01 | -0.6 |

## US100 (proxy NQ) -- día anterior (PDH/PDL) (train)

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 57 | 38.6 | 0.41 | -6.393 | -4.82 | -5.39 |
| Solo verde (retiene 10.5%) | 6 | 50.0 | 0.34 | -2.171 | -0.69 | -0.74 |
| No rojo (verde+neutral) (retiene 56.1%) | 32 | 37.5 | 0.35 | -5.372 | -3.07 | -3.47 |

## US100 (proxy NQ) -- día anterior (PDH/PDL) (test)

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 57 | 52.63 | 0.83 | -1.62 | -1.31 | -3.79 |
| Solo verde (retiene 10.5%) | 6 | 33.33 | 0.45 | -1.875 | -0.62 | -0.99 |
| No rojo (verde+neutral) (retiene 59.6%) | 34 | 47.06 | 0.79 | -1.602 | -1.02 | -2.61 |

## US100 (proxy NQ) -- 4 horas (train)

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 330 | 48.18 | 0.82 | -3.413 | -4.01 | -4.7 |
| Solo verde (retiene 20.3%) | 67 | 43.28 | 0.79 | -1.904 | -0.83 | -1.45 |
| No rojo (verde+neutral) (retiene 77.9%) | 257 | 49.03 | 0.87 | -1.973 | -2.06 | -4.33 |

## US100 (proxy NQ) -- 4 horas (test)

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 319 | 54.23 | 0.98 | -0.405 | -0.44 | -2.5 |
| Solo verde (retiene 14.4%) | 46 | 54.35 | 0.75 | -1.586 | -0.82 | -1.31 |
| No rojo (verde+neutral) (retiene 78.1%) | 249 | 55.82 | 1.01 | 0.263 | 0.18 | -2.02 |

