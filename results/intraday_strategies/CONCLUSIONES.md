# Conclusiones: dos estrategias intradía en el US100 (NQ, 1 min, CME)

Detalle completo en [`report.md`](report.md) y la curva de capital en [`equity_curve.png`](equity_curve.png).
Para reproducir: `python3 scripts/run_intraday_strategies.py`.

## Resumen (neto de costos, ejecución en la vela siguiente a la señal)

| | S1 bandas de ruido (vol-target, como el paper) | S1 (1x) | S2 con VIX ≥ 20 (tu regla) | S2 sin filtro VIX | NQ buy & hold |
|---|---|---|---|---|---|
| Ventana | 13-abr → 14-sep-2026 | ídem | 23-mar → 14-sep-2026 | ídem | 24-mar → 14-sep-2026 |
| Trades | 75 | 75 | **9** | 61 | – |
| Retorno total | +5.87 % | +3.02 % | +0.60 % | +2.91 % | +15.69 % |
| Sharpe | 1.16 | 1.05 | 1.16 | 1.94 | 1.50 |
| **Sortino** | **2.54** | **1.93** | **1.93** | **3.77** | 2.29 |
| Máx. drawdown | −5.14 % | −3.78 % | −0.46 % | −1.36 % | −13.81 % |
| **Alfa anual** (t-stat) | **+15.5 %** (0.73) | **+7.1 %** (0.59) | **+1.1 %** (0.90) | **+6.8 %** (1.54) | – |
| **Beta** vs NQ | **−0.03** | **0.00** | **0.01** | **−0.01** | 1.00 |
| Retorno sin el mejor día | +0.13 % | +0.48 % | +0.11 % | +1.53 % | +11.9 % |
| P(media ≤ 0) bootstrap | 0.18 | 0.22 | 0.15 | 0.05 | 0.15 |

## Cómo leerlo

1. **Beta ≈ 0 en ambas**: como cierran todo antes de las 16:00 y operan en ambos
   sentidos, no dependen de la dirección del mercado. Es lo que reportan los papers
   y se confirma aquí. Por eso su drawdown es mucho menor que el del índice.
2. **Ningún alfa es estadísticamente significativo** (todos los t < 2). Con ~5 meses
   de datos no se puede distinguir un alfa real de la suerte; el IC 90 % del Sharpe
   incluye el 0 en todos los casos.
3. **S1 depende de un solo día**: el 5-jun-2026 (corto en una caída de −3.4 %) aporta
   +5.7 % con apalancamiento de 2.3x. Sin ese día S1 queda plana (+0.13 %). Además es
   sensible al lookback: 14 días da Sharpe ~1, 20 días da Sharpe ≈ 0 o negativo
   (ver tabla de robustez). Es el comportamiento típico de un trend-follower intradía
   (pocos días grandes pagan muchas pérdidas chicas; win rate 39 %), pero 5 meses no
   alcanzan para confirmarlo.
4. **S2 con el filtro VIX ≥ 20 casi no opera** en esta muestra: el VIX estuvo sobre 20
   solo en marzo-abril y un par de días de junio/julio → 9 trades. El resultado
   (+0.6 %, 6 de 9 ganadores) es consistente con el paper pero no es evaluable
   estadísticamente.
5. **S2 sin filtro es lo más sólido de la muestra** (Sharpe 1.94, Sortino 3.77,
   P(media ≤ 0) = 5 %), pero ojo: casi todo vino de la primera mitad (Sharpe 3.9 vs
   0.5 en la segunda), y **solo funciona con la definición del paper** (rendimiento
   desde el cierre de ayer hasta las 10:00). Si la "primera media hora" se mide de
   09:30 a 10:00, el resultado se vuelve negativo (Sharpe −0.84). Es decir, la señal
   útil está en el gap overnight + primera media hora, no en la media hora sola.

## Qué tan confiable es

**Lo que se controló:** sin look-ahead (señal con el precio de la marca, ejecución en la
apertura de la vela siguiente; VIX del cierre del día anterior); costos de 1 tick +
comisión por lado; rolls de contrato detectados y sin mezclar precios de contratos
distintos; feriados NYSE excluidos (el futuro cotiza con sesión recortada ese día);
días de vencimiento con libro ilíquido excluidos; 0 velas duplicadas o inconsistentes;
0 minutos faltantes en los días operables.

**El límite principal es la muestra**: los datos de CME disponibles en el repo cubren
solo ~6 meses (18-mar → 14-sep-2026, 117 días operables). Los papers usan 15-25 años.
Con esto **no se puede afirmar que alguna de las dos sea rentable** de forma confiable;
solo que su comportamiento (beta ≈ 0, perfil de pagos) es consistente con lo publicado.
Para una conclusión seria hace falta historia de varios años (el workflow de Databento
del repo puede bajarla con `--days` mayor, a costo de tu cuota).
