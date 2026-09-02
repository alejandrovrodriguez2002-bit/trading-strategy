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
   la sesión de NY (09:30–09:45 ET, configurable).
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
  synthetic.py     generador de datos sintéticos (solo demo)
scripts/
  download_data.py descarga con yfinance (correr localmente, con internet)
  run_backtest.py   CLI principal: corre el backtest y genera el reporte
tests/             tests unitarios (pytest)
results/           output del último run (trades.csv, métricas, gráfico)
pine/
  ny_orb_cvd_absorption.pine  misma estrategia en Pine Script v5 para
                              TradingView (usa el historial de precios de
                              TradingView directamente, sin exportar/importar
                              datos; Sortino/Sharpe/win rate/profit factor los
                              da nativos el "Strategy Tester" de TradingView)
```

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
