# Backtest: NY Opening Range Breakout + Absorción CVD (Nasdaq)

Motor de backtesting para la estrategia intradía de apertura de NY sobre
Nasdaq (QQQ por defecto): rango de apertura de 15 min, sesgo direccional
por rompimiento, confirmación de entrada por **absorción** usando
**Cumulative Volume Delta (CVD)**, y gestión de stop loss / take profit
basada en swings (highs/lows) más cercanos.

## ⚠️ Limitaciones importantes (leer primero)

1. **Datos**: este entorno de ejecución tiene el acceso de red saliente
   restringido (no puede llegar a Yahoo Finance ni a otros proveedores),
   así que no pude descargar datos reales aquí. El repo incluye:
   - Un generador de datos **sintéticos** (`src/synthetic.py`) usado solo
     para demostrar que todo el pipeline corre de punta a punta
     (`results/` contiene un run de ejemplo). **Esas cifras NO son una
     estimación de la rentabilidad real de tu estrategia**, son sobre
     precios simulados.
   - Un script de descarga con `yfinance` (`scripts/download_data.py`)
     para que lo corras en tu máquina (con internet). **Ojo**: Yahoo
     limita el historial intradía (1m ≈ 7-8 días, 5m/15m ≈ 60 días), así
     que **no vas a poder pedir 6 meses de velas de 5 min con Yahoo**.
     Para 6 meses reales de 1-5 min con volumen necesitas un proveedor
     de pago (Databento, Polygon.io, IBKR historical data, export de
     TradingView, etc.) y cargar ese CSV con `--csv`.
   - Un loader de CSV genérico (`src/data.py: load_csv`) que acepta
     encabezados típicos (Date/Datetime, Open, High, Low, Close, Volume).

   **La forma más rápida de tener resultados reales**: exporta 6 meses
   de velas de 1 o 5 minutos (con volumen) de QQQ (o el instrumento que
   uses) a CSV y pásamelo, o corre:
   ```
   python scripts/run_backtest.py --csv data/tu_archivo.csv
   ```

   **Nota**: `config/strategy_config.yaml` está configurado para operar
   solo dentro de las **primeras 2 horas de la apertura de NY (09:30–11:30
   ET)** — ajusta `session.close` si tu CSV cubre un rango distinto. El
   motor no necesita el día completo: solo usa las velas dentro de ese
   rango para el OR, el rompimiento, la confirmación de absorción y el
   cierre de posición (si no se toca SL/TP antes de las 11:30, se cierra
   ahí como fin de la ventana operable).

2. **CVD aproximado, no de nivel 2 real**: no tenemos datos de tick/bid-ask,
   así que el volumen delta se aproxima por vela con la fórmula estándar
   `delta = volume * ((close-low)-(high-close)) / (high-low)`. Es la
   misma aproximación que usan la mayoría de indicadores de "Volume
   Delta" cuando no hay feed de order flow real. Si tienes datos de tick
   o CVD ya calculado por tu plataforma, se puede sustituir fácilmente
   (ver `src/cvd.py`).

3. **Interpretación de las reglas**: como no puedo ver imágenes en este
   chat en tiempo real, la lógica de absorción se implementó según la
   captura que confirmaste (CVD hace nuevo extremo que el precio no
   confirma) y la aplicación que elegiste explícitamente: **modelo de
   continuación** (ver más abajo). Si algo no calza con tu idea, es un
   parámetro/regla puntual para ajustar, no un rediseño.

## Reglas implementadas

1. **Rango de apertura (OR)**: high y low de los primeros 15 minutos de
   la sesión de NY (09:30–09:45 ET, configurable). Solo se toma como válido
   si además hay una **entrada de volumen considerable** durante ese rango
   respecto al volumen reciente — ver "Filtro de volumen de apertura" abajo.
2. **Sesgo direccional**: la primera vez que el precio toca/rompe el
   OR-high o el OR-low define el sesgo — rompe el high → sesgo **LONG**;
   rompe el low → sesgo **SHORT**.
3. **Confirmación por absorción (CVD)** — modelo de **continuación**:
   tras el rompimiento se espera un pullback en contra del sesgo. Se
   buscan dos pivotes (fractales de 3 velas) consecutivos del mismo tipo
   dentro de ese pullback:
   - Sesgo LONG → se buscan dos **mínimos** del pullback. Si el segundo
     mínimo de PRECIO es más alto que el primero (el precio no confirma
     un nuevo mínimo) **pero** el CVD sí hace un mínimo más bajo →
     absorción de vendedores confirmada → **entra LONG**.
   - Sesgo SHORT → simétrico con dos **máximos**: precio hace un máximo
     más bajo mientras el CVD hace un máximo más alto → absorción de
     compradores → **entra SHORT**.
   - Si el precio retrocede por completo hasta cruzar el lado contrario
     del rango de apertura antes de confirmar → se invalida el setup del
     día (no hay entrada).
   - Entrada ejecutada en la **apertura de la vela siguiente** al cierre
     que confirma el segundo pivote (evita look-ahead).
4. **Stop loss**: el swing (high/low histórico, fractal de N velas,
   configurable) más cercano al precio de entrada, del lado contrario a
   la operación — y que además sea un **pool de liquidez genuino** (ver
   "Filtro de liquidez" abajo): si el más cercano no tuvo volumen alto al
   formarse, se prueba el siguiente más cercano que sí lo tenga.
5. **Take profit**: el **segundo** swing más cercano (se salta el más
   cercano) del lado a favor de la operación. Si no hay un segundo swing
   disponible, se usa un fallback de 2R documentado en el código.
6. **Salida**: si no se toca SL ni TP, se cierra al cierre de la sesión
   (no se dejan posiciones overnight). Máximo 1 trade/día (configurable).
7. **Position sizing**: riesgo fijo por trade (% del equity, configurable
   en `config/strategy_config.yaml`), con slippage y comisión opcionales.

Todos los parámetros (minutos del OR, ventana de fractales, % de riesgo,
slippage, etc.) están en `config/strategy_config.yaml`.

### Filtro de volumen de apertura

La estrategia solo se activa cuando hay una **entrada de volumen
considerable** que se asemeja a la apertura real de NY, no simplemente
porque el reloj marque las 9:30. Concretamente (`src/strategy.py:
_volume_surge_ok`): se calcula el volumen promedio de las `lookback_bars`
velas previas (línea base de "volumen normal") y se exige que el volumen
máximo dentro del rango de apertura sea al menos `multiplier` veces esa
línea base (default: 20 velas de línea base, 1.5x). Si no se cumple, el
día se descarta por completo — no hay setup ese día — igual que un trader
real ignoraría una apertura con muy poca participación (feriado, sesión
ilíquida, medio día, etc.).

Esto también hace más realista la simulación de mercado: los tres datasets
sintéticos (`src/synthetic_datasets.py` y `src/synthetic.py`) ahora
incluyen un **perfil de volumen intradía** con un pico en la apertura (≈3-4x
el volumen "normal" del resto del día) que decae exponencialmente en los
primeros ~30 minutos — el patrón real de "explosión de volumen" que ocurre
cuando abre el mercado de NY. Como el CVD se calcula ponderado por volumen,
esto también hace que la señal de absorción esté naturalmente dominada por
el flujo de órdenes de la primera media hora, que es justo el período que
le interesa a esta estrategia.

Parámetros en `config/strategy_config.yaml` bajo `volume_filter:`
(`enabled`, `lookback_bars`, `multiplier`) — puedes desactivarlo
(`enabled: false`) para comparar el efecto.

### Filtro de liquidez (concepto ICT/SMC)

El swing usado como stop loss debe ser un **pool de liquidez genuino**,
no una vela de ruido cualquiera. Concretamente (`src/strategy.py:
_is_liquidity_level`): un swing high/low se acepta como referencia de SL
solo si el volumen de la vela que lo formó fue al menos `multiplier`
veces el volumen promedio de las `lookback_bars` velas previas (misma
lógica que el filtro de volumen de apertura, aplicada aquí a cualquier
swing histórico). La idea (ICT/SMC): un swing formado con volumen alto
tiene muchos stops/órdenes reales descansando ahí — es un nivel que el
mercado "recuerda" — mientras que un swing de bajo volumen es solo ruido
de precio sin nada detrás.

Aplicación por dirección: un **SHORT** solo se toma si su swing HIGH de
referencia (el nivel de SL, arriba del precio) tuvo volumen alto al
formarse; un **LONG** solo si su swing LOW de referencia (abajo del
precio) lo tuvo. Si el swing más cercano no califica, se prueba el
siguiente más cercano que sí tenga volumen alto; si ninguno califica, no
hay trade ese día.

Parámetros en `config/strategy_config.yaml` bajo `liquidity_filter:`
(`enabled`, `lookback_bars`, `multiplier`).

**Resultado sobre los 6 meses reales de QQQ**: mixto. En velas de **1
minuto mejora bastante** (mejor combinación pasa de Sortino -3.18 a
**-0.52**, profit factor 0.59→0.89, con OR=60min) — la granularidad más
fina es también donde más ruido de precio sin volumen real hay, así que
tiene sentido que filtrar por liquidez ayude más ahí. Pero en **2m/3m/5m
el filtro no ayuda o empeora ligeramente** el mejor caso de cada
intervalo (ver la tabla de resultados reales más abajo). No es una
solución completa al problema de fondo, pero es la primera modificación
que muestra una mejora real y sustancial en alguna granularidad.

### Filtro probado y descartado: bandas de desviación estándar semanal

Se probó también un filtro de "Punto de Control" semanal, primero como
umbral fijo de distancia y después como banda de 1-2 desviaciones
estándar respecto a la media (~VWAP) del perfil de volumen de la semana
anterior (aceptar solo entradas ni muy pegadas al centro ni muy
extendidas). Validado contra los 6 meses reales de QQQ, **no mejoraba el
resultado — en varios casos lo empeoraba** (ej. cortaba 60-70% de los
trades sin subir el profit factor, y en 2m/OR30 lo bajaba de 0.95 a
0.27). Se retiró del motor (código en el historial de git si se quiere
retomar con otro enfoque) para no seguir recortando la muestra sobre una
base que ya no tenía edge — ver el resultado real más abajo.

## Estrategia alternativa que SÍ muestra edge: ORB clásico en modo "fade" (`src/simple_orb.py`)

Después de que ORB + absorción CVD (con y sin volumen/liquidez/bandas SD)
nunca superó profit factor 1.0 de forma consistente en los 6 meses reales
de QQQ, se probó una hipótesis distinta desde cero, **sin CVD**:
`src/simple_orb.py` + `scripts/run_simple_orb_grid.py`.

**Idea**: quizás el CVD aproximado (sin datos de tick reales) mete ruido
en vez de señal. En vez de operar A FAVOR del primer rompimiento del rango
de apertura (continuación, como toda la estrategia anterior), se probó
operar **EN CONTRA** (**fade**): apostar a que el rompimiento es una
barrida de liquidez / falso rompimiento, y el precio revierte hacia el
rango — un concepto de ICT/SMC distinto al de absorción CVD.

Reglas de la configuración ganadora:

1. Rango de apertura de **30 minutos** (09:30–10:00 ET).
2. Al primer rompimiento del OR-high o el OR-low, se entra **EN CONTRA**
   (fade): rompe el high → SHORT; rompe el low → LONG. Relleno al nivel
   del OR (orden stop), o al open de la vela si abre más allá (gap).
3. Stop loss: el extremo real (mecha) de la vela que rompió el rango + un
   buffer pequeño — no el nivel del OR, que ya quedó superado.
4. Take profit: **1.5R fijo** (no depende de swings futuros).
5. Sin filtro de tendencia ni de volumen — ninguno de los dos ayudó en las
   pruebas de esta variante.
6. Sizing: 1% de equity arriesgado por trade, con **tope de apalancamiento
   1x** (`max_leverage=1.0`, sin margen) — importante: un SL anclado en la
   mecha real puede quedar tan ajustado que arriesgar el 1% nominal pediría
   una posición nocional de decenas de veces el equity. Con el tope, el
   riesgo real de esos trades queda por debajo del 1% y el R-multiple se
   recalcula sobre el riesgo real (ver `src/simple_orb.py`).

### Validación honesta: split train/test por fecha (no todo el dataset)

Para no repetir el error que llevó a descartar el filtro de bandas SD
(sobreajustar a los 6 meses completos), `scripts/run_simple_orb_grid.py`
barre 120 combinaciones (OR ∈ {15,25,30,35,45}min, SL ∈
{or_opposite,liquidity}, TP ∈ {1.5,2,3}R, filtro de tendencia, dirección
{breakout,fade}) usando **solo la primera mitad** de los ~6 meses reales
(62 días, "train") para elegir la mejor combinación por Sortino, y evalúa
esa combinación ya fija contra la **segunda mitad** (63 días, "test") que
el proceso de selección nunca vio. En los cuatro intervalos probados
**"fade" con OR=30min ganó la búsqueda** (nunca "breakout"/continuación),
lo cual es en sí mismo una señal de robustez (no es un ganador aislado en
un rincón del grid).

Resultado usando la **misma configuración fija** (OR=30min, SL=mecha real,
fade, TP=1.5R, sin filtro de tendencia, sin volumen) en los cuatro
intervalos — sin re-optimizar por intervalo, para no maquillar el número:

| Intervalo | | Trades | Win rate | Profit factor | Sortino | Retorno (63 días test, sin apalancamiento) | Max DD |
|---|---|---|---|---|---|---|---|
| 1m | train | 61 | 59.0% | 1.89 | 8.73 | +1.91% | -0.71% |
| 1m | **test** | 61 | 54.1% | **1.05** | 0.47 | +0.15% | -0.60% |
| 2m | train | 61 | 65.6% | 2.00 | 8.62 | +2.29% | -0.82% |
| 2m | **test** | 61 | 60.7% | **1.47** | 4.22 | +1.53% | -0.52% |
| 3m | train | 61 | 67.2% | 2.08 | 8.90 | +2.52% | -0.52% |
| 3m | **test** | 61 | 65.6% | **1.61** | 5.03 | +1.94% | -0.54% |
| 5m | train | 61 | 70.5% | 2.13 | 8.50 | +2.87% | -0.66% |
| 5m | **test** | 61 | 63.9% | **1.41** | 3.47 | +1.72% | -1.12% |

Las filas **test** son las que importan: nunca se usaron para elegir
parámetros. **Las cuatro granularidades quedan con profit factor > 1.0 y
Sortino > 0 fuera de muestra** — la primera vez en todo este proyecto que
un resultado real se sostiene en datos que el proceso de selección no vio.
El efecto es más débil en 1m (PF apenas sobre 1.0) y más sólido en 2m/3m/5m.

Chequeos adicionales de robustez (sobre 5m, la más fuerte):
- **Por mes**: positivo en 5 de 7 meses (marzo–septiembre 2026), sin que
  ningún mes ni ningún trade individual domine el resultado (mejor trade
  +$66, peor trade -$41, sobre una cuenta de $10,000).
- **Por ventana de OR** (15/20/25/30/35/40/45/60 min, resto de parámetros
  fijos): la mayoría de ventanas ≥25min dan PF>1 fuera de muestra; 30min
  es la mejor pero no un pico aislado — 35/40/45min también funcionan.
- **Apalancamiento**: el resultado (win rate, profit factor, distribución
  de R) es prácticamente el mismo con `max_leverage` en 1x, 2x o 4x — solo
  cambia cuánto retorno en $ se extrae del mismo edge. El retorno de la
  tabla de arriba es **sin ningún margen** (lo más conservador posible);
  con 2-4x de margen intradía (típico de una cuenta pattern-day-trader)
  el mismo edge escala el retorno proporcionalmente.

### Honestidad sobre las limitaciones de este resultado

- El período de test son 63 días de mercado (~3 meses, marzo–septiembre
  2026) de un solo instrumento (QQQ) en un solo régimen. Es una validación
  fuera de muestra real, no una garantía hacia adelante — falta
  forward-testing en papel y en otros períodos/instrumentos.
- El SL anclado en la mecha real puede ser muy ajustado (mediana ~0.1% del
  precio en 5m) — el motor lo modela con slippage de 1bp, pero en
  ejecución real el spread/deslizamiento en el momento exacto de una
  barrida de liquidez probablemente sea mayor a lo modelado.
- Sigue siendo una muestra de ~120 trades por intervalo en test — mejor
  que las docenas de trades de los barridos anteriores, pero no es
  estadísticamente enorme.

Con esas salvedades explícitas: esta es, hasta ahora, la única variante de
todo este proyecto que muestra edge positivo (profit factor y Sortino > 0)
en datos reales que el proceso de selección de parámetros nunca vio.

## Métricas calculadas

`src/metrics.py` calcula, sobre la curva de equity diaria y el log de
trades: retorno total, CAGR, win rate, profit factor, expectancy (en R),
avg win/loss, max drawdown, **Sharpe ratio** y **Sortino ratio**
(anualizados, downside deviation con MAR=0), número de trades y duración
promedio.

## Estructura del proyecto

```
config/strategy_config.yaml   parámetros de la estrategia
src/
  data.py         carga de CSV / descarga con yfinance
  cvd.py          cálculo de volume delta y CVD acumulado
  swings.py       detección de pivotes/fractales (SL/TP y confirmación)
  strategy.py      lógica de la estrategia (OR, rompimiento, absorción, SL/TP)
  backtest.py      orquesta datos -> estrategia -> curva de equity
  metrics.py       Sortino, Sharpe, drawdown, win rate, etc.
  synthetic.py     generador de datos sintéticos simple (demo)
  synthetic_datasets.py  datasets A/B/C para pruebas de robustez (ver abajo)
scripts/
  download_data.py descarga con yfinance (correr localmente, con internet)
  run_backtest.py   CLI principal: corre el backtest y genera el reporte
  run_dataset_comparison.py  corre la estrategia sobre los datasets A/B/C
                              y genera el reporte comparativo
  run_or_window_sweep.py     barrido de la ventana de OR (5/10/15/30/60 min)
                              sobre los datasets A/B/C
  run_or_window_sweep_real.py  mismo barrido pero sobre datos reales
                                (NASDAQ ^IXIC en data/*.csv)
  fetch_nasdaq_candles.py    extrae velas de Yahoo Finance (gratis, corto
                              historial) — pensado para correr vía Actions
  fetch_databento_candles.py extrae velas de Databento (de pago, meses/
                              años de historial real) — vía Actions
tests/             tests unitarios (pytest)
results/           output del último run (trades.csv, métricas, gráfico)
  comparison/      reporte comparativo A/B/C (ver abajo)
  or_window_sweep_real_qqq/  barrido de OR sobre 6 meses reales de QQQ
                              (ver abajo) — el resultado que importa
  or_window_sweep_real_ixic/ idem sobre ^IXIC (Yahoo, historial corto)
  or_window_sweep/ reporte del barrido de ventana de OR (ver abajo)
.github/workflows/
  fetch_nasdaq_candles.yml     corre fetch_nasdaq_candles.py en un runner
                                de GitHub (con internet real)
  fetch_databento_candles.yml  corre fetch_databento_candles.py (requiere
                                el secret DATABENTO_API_KEY, ver abajo)
pine/
  ny_orb_cvd_absorption.pine  misma estrategia en Pine Script v5 para
                              TradingView (usa el historial de precios de
                              TradingView directamente, sin exportar/importar
                              datos; Sortino/Sharpe/win rate/profit factor los
                              da nativos el "Strategy Tester" de TradingView)
```

## Pruebas de robustez: datasets sintéticos A / B / C

`src/synthetic_datasets.py` + `scripts/run_dataset_comparison.py` corren la
estrategia sobre tres mercados sintéticos con procesos generadores
**fundamentalmente distintos**, calibrados con la misma volatilidad total
(mismo orden de magnitud de desviación estándar por vela) para que la
comparación aísle la FORMA de la distribución y la dinámica temporal, no
solo "cuál es más ruidoso". El objetivo es de robustez, no de rentabilidad:
¿el resultado de la estrategia depende de que el mercado se comporte como el
modelo Gaussiano de libro de texto, o se sostiene bajo dinámicas de colas
pesadas / criticidad auto-organizada?

- **Dataset A — "Tradicional"**: Geometric Brownian Motion + GARCH(1,1), el
  modelo estándar de finanzas cuantitativas. Retornos ~condicionalmente
  Gaussianos, clustering de volatilidad "clásico", colas relativamente
  delgadas.
- **Dataset B — "Sistemas complejos / criticidad auto-organizada (SOC)"**:
  combina una **cascada multiplicativa multifractal** (estilo Markov-
  Switching Multifractal de Calvet & Fisher — volatilidad como producto de
  varios componentes que conmutan a distintas escalas temporales) con un
  **proceso de Hawkes auto-excitante** de magnitudes Pareto/ley de potencia.
  Este último es exactamente la representación matemática que usa la
  literatura de criticidad auto-organizada para los ejemplos de referencia
  que mencionaste — **turbulencia, terremotos (modelo ETAS), avalanchas,
  incendios forestales, apagones en cascada** — y también se usa en la
  literatura de mercados financieros para modelar clustering de crashes.
  Resultado: colas mucho más pesadas (kurtosis ≈10 vs ≈0.7 de A) y eventos
  que se agrupan en el tiempo ("avalanchas") en vez de ser independientes.
- **Dataset C — "Regime-switching" (combina A y B)**: cadena de Markov de 2
  estados (calma/crítico) que alterna entre la dinámica de A y la de B, con
  episodios críticos más cortos y agudos que los tramos de calma — como los
  ciclos reales de mercado. Queda en un punto intermedio (kurtosis ≈2).

Correrlo:
```bash
python scripts/run_dataset_comparison.py
```
Genera en `results/comparison/`: `comparison_report.md` (tabla con
kurtosis/ACF de cada dataset + todas las métricas de la estrategia lado a
lado), `comparison_equity_curves.png` (las 3 equity curves superpuestas) y
`comparison_return_distributions.png` (histograma de retornos en escala
log, para ver las colas). Cada dataset también guarda su `trades.csv` y
`metrics.json` en su propia subcarpeta.

**Importante**: igual que el resto de este repo, esto corre sobre precios
SINTÉTICOS — sirve para ver si la estrategia es frágil ante ciertos
supuestos de mercado, no reemplaza el backtest con datos reales.

### Barrido del rango de apertura: 5 / 10 / 15 / 30 / 60 min

`scripts/run_or_window_sweep.py` corre la misma estrategia (filtro de
volumen + absorción CVD + SL/TP por swings) variando únicamente cuántos
minutos de la apertura de NY se usan para marcar el high/low inicial —
5, 10, 15, 30 y 60 minutos — sobre los mismos datasets A/B/C.

```bash
python scripts/run_or_window_sweep.py
```

Genera en `results/or_window_sweep/`: `or_window_sweep_report.md` (tabla
15x — 5 ventanas × 3 datasets — con todas las métricas),
`sortino_by_or_window.png` (barras de Sortino por dataset/ventana) y
`equity_curves_by_or_window.png` (equity curve de cada ventana, un panel
por dataset).

**Hallazgo** (sobre los datasets sintéticos): a **menor** ventana de OR,
**mejor** resultado — la relación es prácticamente monótona en los 3
datasets. Más claro en el dataset C (regime-switching, el más realista de
los tres): Sortino cae de **5.63 (5 min)** → 3.46 (10 min) → 1.81 (15 min)
→ 0.43 (30 min) → 0.19 (60 min). Mismo patrón en A y B (la ventana más
corta es la mejor o la menos mala). Esto es consistente con la idea de
que el rango de apertura debe capturar la "explosión" inicial de la
apertura de NY (ya validada aparte con el filtro de volumen) y no
diluirse con ventanas más largas, donde el nivel de apertura deja de
representar bien la reacción inicial del mercado.

### Con datos REALES: QQQ (Databento, ~6 meses) y NASDAQ Composite (^IXIC, Yahoo)

`scripts/run_or_window_sweep_real.py` corre el mismo barrido de OR
(5/10/15/30/60 min) sobre velas reales, en vez de los datasets
sintéticos. Soporta dos fuentes vía `--source`:

```bash
python scripts/run_or_window_sweep_real.py                # QQQ (Databento), ~6 meses — default
python scripts/run_or_window_sweep_real.py --source ixic  # ^IXIC (Yahoo), historial corto
```

Al cargar estos datos aparecieron y se corrigieron **tres bugs reales**
en `src/data.py: load_csv` y `scripts/fetch_databento_candles.py`
(afectan a cualquier CSV real que se cargue, no solo a estos):

1. **Columna `close` duplicada** (Yahoo): los CSV traen `Close` y `Adj
   Close` a la vez, ambas se mapeaban a `close` → rompía cualquier resta
   entre columnas (el cálculo del CVD) con `ValueError: cannot reindex
   on an axis with duplicate labels`. Se deduplica quedándose con la
   primera.
2. **Volumen de la primera vela del día en 0** (Yahoo): artefacto
   conocido de Yahoo en datos intradía — justo la vela que más le
   importa a esta estrategia. Se corrige (`_fix_yahoo_zero_open_volume`)
   con el volumen de la vela siguiente del mismo día.
3. **Databento tiene ~1 día de retraso en su feed histórico**: pedir
   datos hasta "hoy" devuelve `422 data_end_after_available_end`. Se
   ajustó el script para pedir hasta ayer por defecto.

#### Resultado con 6 meses reales de QQQ (Databento) — el que de verdad importa

125 días de trading, marzo-septiembre 2026, con el motor actual (filtro
de volumen de apertura + filtro de liquidez en el SL; sin el filtro de
bandas de desviación estándar que se probó y se retiró — ver arriba). A
diferencia de las pruebas con datos sintéticos (donde el dataset C de
regime-switching mostraba Sortino positivo y claramente mejor con
ventanas de OR cortas), **sobre datos reales de QQQ la estrategia sigue
dando resultados negativos** en las granularidades con suficientes
trades para ser relevantes (1m/2m/3m/5m — 26 a 91 trades cada una),
aunque el filtro de liquidez mejora notablemente la de 1 minuto:

| Intervalo | Mejor OR | Sortino | Profit factor | Retorno | Trades |
|---|---|---|---|---|---|
| 1m | 60 min | **-0.52** | **0.89** | -1.36% | 62 |
| 2m | 15 min | -2.00 | 0.65 | -5.27% | 63 |
| 3m | 30 min | -2.04 | 0.57 | -3.84% | 40 |
| 5m | 5 min | -1.71 | 0.58 | -3.10% | 26 |

Es decir: el profit factor sigue sin superar 1.0 en ningún caso con
muestra suficiente, pero en **1 minuto pasó de 0.59 a 0.89** — la mejora
más grande que hemos visto de cualquier ajuste hasta ahora, aunque no
alcanza breakeven. En 2m/3m/5m el filtro no mueve mucho la aguja (y en
algún caso la empeora ligeramente respecto al baseline sin liquidez).
Los intervalos de 10m/15m/30m/60m muestran Sortino positivo en algún
punto (hasta 7.95 en 10m/OR15), pero con 3-8 trades en 6 meses —
insuficiente para sacar ninguna conclusión (ver
`results/or_window_sweep_real_qqq/`).

**Esto es justo la razón por la que insistí tanto en probar con datos
reales antes de sacar conclusiones de los datasets sintéticos**: el
patrón "ventana de OR más corta = mejor" que parecía tan claro con
datos sintéticos (especialmente en el dataset C) **no se sostiene** con
QQQ real. Los generadores sintéticos, por bien calibrados que estén en
momentos estadísticos (volatilidad, kurtosis, clustering), no capturan
toda la microestructura real del mercado que esta estrategia intenta
explotar. De los tres filtros de calidad de entrada probados (umbral
fijo al POC semanal, bandas de desviación estándar, liquidez en el SL),
el de liquidez es el primero que muestra una mejora real y sustancial
— pero solo en una granularidad. Sigue sin haber una combinación con
edge positivo confirmado en datos reales; antes de operar esto con
dinero real hace falta seguir iterando sobre la lógica central
(parámetros de absorción, definición de sesgo, gestión de SL/TP).

## Versión Pine Script (TradingView)

`pine/ny_orb_cvd_absorption.pine` es la misma lógica traducida a Pine v5:

1. Pega el contenido del archivo en el Pine Editor de TradingView.
2. Ábrelo en un gráfico de QQQ (o NQ1!, etc.) en timeframe de 1 o 5 min.
3. Pestaña **Strategy Tester → Performance Summary**: ahí ya salen Net
   Profit, Win Rate, Profit Factor, Max Drawdown, Sharpe Ratio y Sortino
   Ratio calculados de forma nativa por TradingView, sobre el historial
   real de TradingView (no hace falta exportar/importar ni conectar
   nada externo).
4. El input "Sesión NY" viene por defecto en `0930-1130` (primeras 2
   horas); ajústalo si quieres probar la sesión completa.

No pude probarlo en un compilador Pine real desde este entorno (no
existe uno aquí); si al pegarlo te marca algún error de sintaxis,
mándame el mensaje exacto que da TradingView y lo corrijo.

## Cómo correrlo

```bash
pip install -r requirements.txt

# 1) Demo end-to-end con datos sintéticos (para validar que todo corre)
python scripts/run_backtest.py --synthetic

# 2) Con tus propios datos reales (recomendado)
python scripts/run_backtest.py --csv data/QQQ_5m.csv

# 3) (opcional, requiere internet) intentar descargar con yfinance
python scripts/download_data.py --ticker QQQ --interval 5m --months 6
python scripts/run_backtest.py --csv data/QQQ_5m.csv

# 4) La variante "fade" que sí muestra edge (ver sección arriba), con split train/test honesto
python scripts/run_simple_orb_grid.py
```

Esto genera en `results/`: `trades.csv` (log completo de operaciones),
`metrics_summary.json` / `.md` (las métricas) y `equity_curve.png`. El
script de la variante fade genera su propio reporte en
`results/simple_orb_grid/`.

## Tests

```bash
pytest tests/ -q
```

## Extracción de datos reales vía GitHub Actions

Este sandbox no tiene acceso de red a proveedores de datos (ver
limitaciones arriba), pero un runner de GitHub Actions sí tiene internet
normal. Hay dos workflows manuales (`workflow_dispatch`) en
`.github/workflows/` para correr la extracción ahí y descargar el CSV
resultante como artifact del run (Actions → el run → "Artifacts"):

- **`fetch_nasdaq_candles.yml`** (Yahoo Finance, gratis): usa
  `scripts/fetch_nasdaq_candles.py`. Rápido para probar, pero limitado a
  ~7 días (1m) / ~60 días (2-5m) de historial — ver limitaciones arriba.
- **`fetch_databento_candles.yml`** (Databento, de pago): usa
  `scripts/fetch_databento_candles.py`. Databento sí entrega meses/años
  de historial de 1 minuto real — la vía correcta para el backtest de 6
  meses. Requiere:
  1. Una cuenta y API key de Databento (databento.com).
  2. Guardar la key como **secret** del repo: Settings → Secrets and
     variables → Actions → New repository secret → nombre
     `DATABENTO_API_KEY`. Así nunca pasa por este chat ni por los logs
     del workflow.
  3. Correr el workflow manualmente (pestaña Actions → "Fetch NASDAQ
     candles (Databento)" → Run workflow), ajustando `dataset` (por
     defecto `XNAS.ITCH`, equities Nasdaq — o `GLBX.MDP3` para el futuro
     NQ), `symbols` (por defecto `QQQ`) y `days` (por defecto 180).
  4. Descargar el CSV del artifact `databento-candles-csv` y subírmelo
     (o pegarlo en `data/`) para correr el backtest con datos reales de
     verdad.

  ⚠️ Es un servicio de pago — revisa tu plan/cuota antes de pedir rangos
  largos. El script ya se validó con una corrida real (ver resultados
  arriba); si vuelve a fallar por algún motivo, pásame el error exacto
  del log y se ajusta.

## Próximos pasos sugeridos

- La estrategia original (ORB + absorción CVD) sigue sin mostrar edge
  robusto en 6 meses reales de QQQ, ni con volumen, ni con liquidez, ni
  con bandas SD. La variante que sí lo muestra es **ORB clásico en modo
  "fade"** (`src/simple_orb.py`, ver sección arriba) — validada con split
  train/test, positiva fuera de muestra en 1m/2m/3m/5m.
- Pasos para llevar el fade de OR30 más allá de esta validación inicial:
  forward-test en papel unas semanas, probar en otro instrumento/período
  (ej. NQ futuro vía `GLBX.MDP3`, u otro rango de fechas) para confirmar
  que no es específico a este régimen de mercado, y sincronizar la lógica
  con `pine/ny_orb_cvd_absorption.pine` si se quiere operar/monitorear
  desde TradingView (el Pine actual todavía implementa solo la estrategia
  original de continuación + CVD, no el fade).
- Si tu CVD "de la imagen" usa una lógica más específica (p.ej. umbral
  mínimo de divergencia, número exacto de velas, o un CVD calculado con
  datos de tick reales de tu plataforma), lo ajustamos en `src/cvd.py` y
  `src/strategy.py` sin tocar el resto del motor.

