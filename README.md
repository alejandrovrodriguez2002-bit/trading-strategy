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
   la operación.
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
tests/             tests unitarios (pytest)
results/           output del último run (trades.csv, métricas, gráfico)
  comparison/      reporte comparativo A/B/C (ver abajo)
  or_window_sweep/ reporte del barrido de ventana de OR (ver abajo)
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
```

Esto genera en `results/`: `trades.csv` (log completo de operaciones),
`metrics_summary.json` / `.md` (las métricas) y `equity_curve.png`.

## Tests

```bash
pytest tests/ -q
```

## Próximos pasos sugeridos

- Pasarme un CSV real de 6 meses (1m o 5m, con volumen) para correr el
  backtest de verdad y afinar parámetros (ventana de absorción, buffer
  de SL, % de riesgo).
- Si tu CVD "de la imagen" usa una lógica más específica (p.ej. umbral
  mínimo de divergencia, número exacto de velas, o un CVD calculado con
  datos de tick reales de tu plataforma), lo ajustamos en `src/cvd.py` y
  `src/strategy.py` sin tocar el resto del motor.
