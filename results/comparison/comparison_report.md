# Comparación de robustez: ORB + Absorción CVD sobre 3 mercados sintéticos

Los tres datasets tienen volatilidad total comparable (mismo orden de magnitud de `ret_std`); lo que cambia es la FORMA de la distribución y la dinámica temporal (colas, clustering), para aislar si el resultado de la estrategia depende de supuestos de mercado 'tradicionales'.

| dataset | ret_std | excess_kurtosis | acf_r2_lag1 | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Dataset A — GBM + GARCH(1,1) (tradicional) | 0.00319 | 0.71 | 0.191 | 31 | -10.38 | 38.71 | 0.28 | -0.35 | -11.89 | -3.477 | -3.883 |
| Dataset B — Cascada multifractal + Hawkes power-law (SOC) | 0.00288 | 9.8 | 0.241 | 23 | -6.24 | 39.13 | 0.37 | -0.277 | -8.72 | -2.408 | -2.769 |
| Dataset C — Regime-switching (A↔B) | 0.00299 | 1.94 | 0.148 | 26 | -3.56 | 46.15 | 0.64 | -0.136 | -6.15 | -1.27 | -1.634 |

**Nota**: estos resultados son sobre precios SINTÉTICOS — sirven para ver si la estrategia es frágil ante colas pesadas / criticidad auto-organizada, no como estimación de rentabilidad real.
