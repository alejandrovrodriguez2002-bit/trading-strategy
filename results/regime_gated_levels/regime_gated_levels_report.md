# Filtro de régimen (Market Regime v7) por nivel

Misma receta fade ya validada (SL en la mecha real, TP=1.5R fijo, sin filtros de tendencia/volumen, `max_leverage=1.0`) aplicada a 3 niveles de referencia (apertura OR30, PDH/PDL, vela de 4h), con y sin el filtro de régimen (`Market Regime v7` portado a Python, solo se opera en ESTRUCTURADO/verde). Split honesto train/test por fecha.

## QQQ -- apertura (OR30) (train)

Retiene 13.3% de los trades ungated tras el filtro de régimen.

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 60 | 66.67 | 1.5 | 4.088 | 2.07 | -1.12 |
| con filtro | 8 | 75.0 | 2.75 | 4.912 | 0.63 | -0.21 |

## QQQ -- apertura (OR30) (test)

Retiene 18.0% de los trades ungated tras el filtro de régimen.

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 61 | 59.02 | 1.2 | 1.876 | 0.79 | -1.62 |
| con filtro | 11 | 63.64 | 1.04 | 0.178 | 0.03 | -0.47 |

## QQQ -- día anterior (PDH/PDL) (train)

Retiene 16.1% de los trades ungated tras el filtro de régimen.

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 56 | 48.21 | 0.7 | -2.979 | -2.35 | -2.84 |
| con filtro | 9 | 44.44 | 0.44 | -2.216 | -0.71 | -0.95 |

## QQQ -- día anterior (PDH/PDL) (test)

Retiene 18.5% de los trades ungated tras el filtro de régimen.

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 54 | 51.85 | 0.5 | -4.736 | -3.52 | -3.67 |
| con filtro | 10 | 70.0 | 1.24 | 0.825 | 0.14 | -0.51 |

## QQQ -- 4 horas (train)

Retiene 18.7% de los trades ungated tras el filtro de régimen.

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 107 | 54.21 | 0.92 | -1.016 | -0.94 | -2.65 |
| con filtro | 20 | 45.0 | 0.36 | -3.19 | -1.49 | -1.56 |

## QQQ -- 4 horas (test)

Retiene 18.9% de los trades ungated tras el filtro de régimen.

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 95 | 50.53 | 0.65 | -4.169 | -3.46 | -3.63 |
| con filtro | 18 | 66.67 | 1.76 | 4.79 | 0.61 | -0.3 |

## US100 (proxy NQ) -- apertura (OR30) (train)

Retiene 5.0% de los trades ungated tras el filtro de régimen.

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 60 | 65.0 | 1.66 | 5.462 | 1.9 | -0.7 |
| con filtro | 3 | 0.0 | 0.0 | -3.364 | -0.45 | -0.45 |

## US100 (proxy NQ) -- apertura (OR30) (test)

Retiene 6.5% de los trades ungated tras el filtro de régimen.

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 62 | 64.52 | 1.43 | 3.622 | 1.81 | -1.12 |
| con filtro | 4 | 75.0 | 1.55 | 1.103 | 0.13 | -0.24 |

## US100 (proxy NQ) -- día anterior (PDH/PDL) (train)

Retiene 10.5% de los trades ungated tras el filtro de régimen.

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 57 | 38.6 | 0.41 | -6.393 | -4.82 | -5.39 |
| con filtro | 6 | 50.0 | 0.34 | -2.171 | -0.69 | -0.74 |

## US100 (proxy NQ) -- día anterior (PDH/PDL) (test)

Retiene 10.5% de los trades ungated tras el filtro de régimen.

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 57 | 52.63 | 0.83 | -1.62 | -1.31 | -3.79 |
| con filtro | 6 | 33.33 | 0.45 | -1.875 | -0.62 | -0.99 |

## US100 (proxy NQ) -- 4 horas (train)

Retiene 20.3% de los trades ungated tras el filtro de régimen.

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 330 | 48.18 | 0.82 | -3.413 | -4.01 | -4.7 |
| con filtro | 67 | 43.28 | 0.79 | -1.904 | -0.83 | -1.45 |

## US100 (proxy NQ) -- 4 horas (test)

Retiene 14.4% de los trades ungated tras el filtro de régimen.

| | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|
| sin filtro | 319 | 54.23 | 0.98 | -0.405 | -0.44 | -2.5 |
| con filtro | 46 | 54.35 | 0.75 | -1.586 | -0.82 | -1.31 |

