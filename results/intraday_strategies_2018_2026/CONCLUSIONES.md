# Conclusiones: dos estrategias intradía en el US100 (NQ, 1 min, CME) — sep-2018 a sep-2026

Detalle completo en [`report.md`](report.md), curva de capital en [`equity_curve.png`](equity_curve.png),
operaciones en `trades_*.csv` y 36 + 48 variantes de robustez en `robustness.csv`.

Datos: 786 521 velas de 1 min del futuro E-mini Nasdaq-100 (`NQ.c.0`, CME Globex vía Databento),
sesión regular, descargadas con el workflow del repo a la rama `data-exports-nq-rth-long`.
Reproducir:

```bash
git show origin/data-exports-nq-rth-long:data/databento_NQ_c_0_1m_candles.csv > data/raw_NQ_c_0_1m_long.csv
python3 scripts/run_intraday_strategies.py --raw data/raw_NQ_c_0_1m_long.csv \
    --out results/intraday_strategies_2018_2026 --clean data/clean_2018_2026
```

## Resultados (8 años, 1 873 días operables, neto de costos)

| | S1 bandas de ruido (vol-target, como el paper) | S1 (1x, sin apalancar) | S2 con VIX ≥ 20 (tu regla) | S2 sin filtro | NQ buy & hold |
|---|---|---|---|---|---|
| Trades | 1 522 | 1 522 | 380 | 991 | – |
| Retorno total | **+281.9 %** | +146.2 % | +10.4 % | +3.7 % | +230.1 % |
| CAGR | 19.9 % | 13.0 % | 1.3 % | 0.5 % | 16.6 % |
| Volatilidad anual | 14.4 % | 9.0 % | 3.8 % | 4.3 % | 24.4 % |
| Sharpe | 1.34 | 1.40 | 0.37 | 0.13 | 0.75 |
| **Sortino** | **2.63** (IC90 % 1.57–3.79) | **2.76** (1.74–3.93) | **0.64** (−0.41–1.93) | **0.22** | 1.07 |
| Máx. drawdown | −12.9 % | **−6.2 %** | −7.1 % | −13.3 % | −39.3 % |
| **Alfa anual** (t-stat) | **+20.6 % (4.38)** | **+13.0 % (4.76)** | +0.8 % (0.61) | +0.2 % (0.13) | – |
| **Beta** vs NQ | **−0.03** | **0.01** | **0.02** | **0.02** | 1.00 |
| Win rate / profit factor | 40 % / 1.32 | 40 % / 1.35 | 49 % / 1.18 | 48 % / 1.04 | – |

## Veredicto

**S1 — Momentum con bandas de ruido + trailing stop (Zarattini et al.): SÍ, robusta.**
* Alfa de +13 % a +21 % anual con t ≈ 4.4–4.8 (p < 0.001) y beta ≈ 0: la ganancia no
  viene de estar expuesto al Nasdaq. El Sharpe de 1.34 es prácticamente el mismo que
  reporta el paper para SPY (1.33).
* Ganó más que comprar y mantener el Nasdaq, con un tercio de su caída máxima (−12.9 % vs −39.3 %).
* Las 36 variantes probadas (lookback 10/14/20, con y sin apalancamiento, precio de
  ejecución, costos ×0/×1/×2) dan retorno positivo. El Sharpe va de 0.94 a 1.51.
* Fue positiva en 8 de 9 años calendario (2018 y 2026 parciales). Solo 2019 cerró en
  −5 % con vol-target (+0.4 % sin apalancar). 2022 (+31 %) fue su mejor año, el mismo
  en que el NQ cayó ~−36 %.
* Lo que hay que vigilar: 2025-2026 se ve más débil (Sharpe 0.9 y 0.5). Además, el
  win rate es de 40 %: pierde seguido y gana poco pero en días grandes, así que las
  rachas perdedoras de semanas son normales.

**S2 — La primera media hora predice la última (Gao et al.) con filtro VIX ≥ 20: NO es rentable de forma confiable.**
* +10 % en 8 años, Sharpe 0.37, alfa no significativa (t = 0.61). Prácticamente todo
  vino de 2020 (+13.7 %, el crash del COVID). Perdió en 5 de los 9 años calendario.
* El filtro VIX sí ayuda: sin filtro el resultado es ≈ 0 (Sharpe 0.13). El efecto
  aparece en alta volatilidad, como dice el paper, pero en el NQ 2018-2026 es demasiado
  débil para cubrir costos de forma consistente. Esto es consistente con la evidencia
  de que la anomalía se ha debilitado desde que se publicó.

## Qué tan confiable es

* **Sin look-ahead:** la señal se calcula con el precio de la marca y se ejecuta en la
  apertura de la vela siguiente. Bandas, volatilidad y VIX usan solo días anteriores.
* **Costos:** 1 tick de slippage + comisión por lado. S1 sigue con Sharpe ≥ 0.96
  incluso con el doble de costos (ver `robustness.csv`).
* **Calidad de datos:**
  * 0 duplicados, 0 velas inconsistentes y 0 minutos faltantes en los días operados.
  * Rolls trimestrales detectados: nunca se mezclan precios de contratos distintos.
  * Excluidos: feriados de NYSE (incluye Juneteenth desde 2022 y cierres por funerales
    de Estado), cierres anticipados a las 13:00 y la semana previa a cada vencimiento
    con volumen < 35 % de lo normal.
  * También se excluyeron 4 días de marzo-2020 con halts por circuit breaker (~14 min
    sin cotizar). Esto probablemente *subestima* a S1, que gana en días de pánico.
* **Lo que el backtest no modela:** el tamaño fraccional de contratos (con poco capital
  conviene usar MNQ, el micro de 2 USD/pt) y el slippage extra en días de muy baja
  liquidez.
* **El VIX de 23-29 sep 2026 aún no está publicado** en la fuente usada. Esos días S2 con
  filtro no opera, lo cual no cambia nada porque el VIX estaba en ~15.

Los resultados del primer análisis (solo 6 meses, mar-sep 2026) siguen en
`results/intraday_strategies/`. Eran demasiado cortos para concluir algo, como se advirtió.
