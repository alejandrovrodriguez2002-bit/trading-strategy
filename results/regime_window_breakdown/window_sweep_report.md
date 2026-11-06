# Ventana de persistencia del régimen + desglose rojo/neutral/verde

## 1) Barrido de ventana de persistencia (N velas antes del rompimiento)

Mejor Sortino (test) por nivel/instrumento/modo, con la ventana N que lo logra:

### QQQ

| Nivel | Modo | Mejor N | Sortino (test) | Profit factor (test) | Trades (test) |
|---|---|---|---|---|---|
| apertura (OR30) | green_only | 10 | 1.734 | 1.86 | 4 |
| apertura (OR30) | not_red | 20 | 0.742 | 1.1 | 31 |
| día anterior (PDH/PDL) | green_only | 10 | 4.605 | 3.28 | 7 |
| día anterior (PDH/PDL) | not_red | 50 | -0.391 | 0.93 | 27 |
| 4 horas | green_only | 1 | 4.79 | 1.76 | 18 |
| 4 horas | not_red | 50 | -2.393 | 0.73 | 46 |

### US100 (proxy NQ)

| Nivel | Modo | Mejor N | Sortino (test) | Profit factor (test) | Trades (test) |
|---|---|---|---|---|---|
| apertura (OR30) | green_only | 1 | 1.103 | 1.55 | 4 |
| apertura (OR30) | not_red | 20 | 3.224 | 1.7 | 16 |
| día anterior (PDH/PDL) | green_only | 50 | 0.0 | nan | 0 |
| día anterior (PDH/PDL) | not_red | 1 | -1.602 | 0.79 | 34 |
| 4 horas | green_only | 20 | 1.329 | 1.39 | 15 |
| 4 horas | not_red | 50 | 5.602 | 1.43 | 121 |

## 2) Desglose por régimen en la vela de rompimiento (sin filtrar, histórico completo)

### QQQ

| Nivel | Régimen | Trades | Win rate % | R promedio | Profit factor |
|---|---|---|---|---|---|
| apertura (OR30) | VOLÁTIL (rojo) | 31 | 67.7 | 0.602 | 1.21 |
| apertura (OR30) | NEUTRAL | 71 | 59.2 | 0.37 | 1.36 |
| apertura (OR30) | ESTRUCTURADO (verde) | 19 | 68.4 | 0.6 | 1.66 |
| día anterior (PDH/PDL) | VOLÁTIL (rojo) | 27 | 55.6 | 0.304 | 1.05 |
| día anterior (PDH/PDL) | NEUTRAL | 65 | 44.6 | 0.044 | 0.46 |
| día anterior (PDH/PDL) | ESTRUCTURADO (verde) | 19 | 57.9 | 0.35 | 0.7 |
| 4 horas | VOLÁTIL (rojo) | 42 | 59.5 | 0.397 | 1.39 |
| 4 horas | NEUTRAL | 123 | 48.8 | 0.14 | 0.64 |
| 4 horas | ESTRUCTURADO (verde) | 38 | 55.3 | 0.258 | 0.71 |

### US100 (proxy NQ)

| Nivel | Régimen | Trades | Win rate % | R promedio | Profit factor |
|---|---|---|---|---|---|
| apertura (OR30) | VOLÁTIL (rojo) | 63 | 69.8 | 0.631 | 2.17 |
| apertura (OR30) | NEUTRAL | 52 | 61.5 | 0.422 | 1.18 |
| apertura (OR30) | ESTRUCTURADO (verde) | 7 | 42.9 | -0.022 | 0.54 |
| día anterior (PDH/PDL) | VOLÁTIL (rojo) | 49 | 51.0 | 0.196 | 0.69 |
| día anterior (PDH/PDL) | NEUTRAL | 54 | 42.6 | -0.012 | 0.62 |
| día anterior (PDH/PDL) | ESTRUCTURADO (verde) | 12 | 41.7 | -0.032 | 0.4 |
| 4 horas | VOLÁTIL (rojo) | 143 | 46.9 | 0.045 | 0.75 |
| 4 horas | NEUTRAL | 393 | 53.7 | 0.191 | 0.99 |
| 4 horas | ESTRUCTURADO (verde) | 113 | 47.8 | 0.075 | 0.77 |

