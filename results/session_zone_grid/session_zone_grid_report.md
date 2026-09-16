# Zonas de valor de 30 min (Asia/Londres/NY, primeros y últimos) sobre NQ real

Misma receta ya validada (fade + SL en la mecha real + TP de 1.5R fijo, sin filtro de tendencia ni de volumen, `max_leverage=1.0` sin margen) aplicada, SIN re-optimizar nada, a 6 zonas horarias de 30 min distintas. Split honesto por fecha: primera mitad del historial de NQ (~180 días) como referencia, segunda mitad ("test") nunca usada para elegir parámetros.

## 5m

- Train: 77 días (hasta antes de 2026-06-16)
- Test: 78 días (desde 2026-06-16, fuera de muestra)

| Zona | | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|---|
| asia_first30 | train | 63 | 34.92 | 0.56 | -4.505 | -1.66 | -1.89 |
| asia_first30 | **test** | 64 | 37.5 | 0.44 | -5.696 | -2.27 | -2.36 |
| asia_last30 | train | 61 | 31.15 | 0.38 | -6.329 | -2.97 | -3.31 |
| asia_last30 | **test** | 63 | 49.21 | 0.81 | -1.754 | -0.74 | -1.28 |
| london_first30 | train | 63 | 47.62 | 0.72 | -2.425 | -0.92 | -1.37 |
| london_first30 | **test** | 65 | 50.77 | 0.93 | -0.647 | -0.22 | -0.78 |
| london_last30 | train | 61 | 57.38 | 1.16 | 1.226 | 0.57 | -0.8 |
| london_last30 | **test** | 64 | 42.19 | 0.59 | -4.163 | -1.79 | -2.31 |
| ny_first30 | train | 60 | 65.0 | 1.66 | 4.862 | 1.9 | -0.7 |
| ny_first30 | **test** | 62 | 64.52 | 1.43 | 3.281 | 1.81 | -1.12 |
| ny_last30 | train | 56 | 50.0 | 0.71 | -1.815 | -1.25 | -1.99 |
| ny_last30 | **test** | 57 | 50.88 | 0.93 | -0.41 | -0.27 | -1.07 |

## 15m

- Train: 77 días (hasta antes de 2026-06-16)
- Test: 78 días (desde 2026-06-16, fuera de muestra)

| Zona | | num_trades | win_rate_pct | profit_factor | sortino_ratio | total_return_pct | max_drawdown_pct |
|---|---|---|---|---|---|---|---|
| asia_first30 | train | 59 | 35.59 | 0.37 | -5.564 | -3.54 | -3.66 |
| asia_first30 | **test** | 60 | 41.67 | 0.52 | -4.332 | -2.42 | -2.77 |
| asia_last30 | train | 57 | 38.6 | 0.4 | -5.663 | -3.59 | -3.66 |
| asia_last30 | **test** | 54 | 44.44 | 0.57 | -3.902 | -2.39 | -3.04 |
| london_first30 | train | 63 | 57.14 | 0.83 | -1.41 | -0.68 | -1.1 |
| london_first30 | **test** | 63 | 52.38 | 0.95 | -0.461 | -0.19 | -0.85 |
| london_last30 | train | 59 | 69.49 | 1.59 | 3.938 | 2.08 | -0.91 |
| london_last30 | **test** | 63 | 46.03 | 0.62 | -3.612 | -2.46 | -3.48 |
| ny_first30 | train | 60 | 70.0 | 1.52 | 3.452 | 2.28 | -0.8 |
| ny_first30 | **test** | 61 | 68.85 | 1.16 | 1.097 | 1.06 | -1.7 |
| ny_last30 | train | 54 | 50.0 | 0.68 | -2.338 | -1.49 | -1.77 |
| ny_last30 | **test** | 57 | 59.65 | 1.24 | 1.339 | 0.96 | -1.01 |

