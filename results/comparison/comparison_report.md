# Comparación de robustez: ORB + Absorción CVD sobre 3 mercados sintéticos

Los tres datasets tienen volatilidad total comparable (mismo orden de magnitud de `ret_std`); lo que cambia es la FORMA de la distribución y la dinámica temporal (colas, clustering), para aislar si el resultado de la estrategia depende de supuestos de mercado 'tradicionales'.

| dataset | ret_std | excess_kurtosis | acf_r2_lag1 | num_trades | total_return_pct | win_rate_pct | profit_factor | expectancy_R | max_drawdown_pct | sharpe_ratio | sortino_ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Dataset A — GBM + GARCH(1,1) (tradicional) | 0.0032 | 0.7 | 0.192 | 29 | -4.5 | 37.93 | 0.58 | -0.156 | -5.03 | -1.629 | -2.054 |
| Dataset B — Cascada multifractal + Hawkes power-law (SOC) | 0.0029 | 9.7 | 0.241 | 28 | -2.93 | 35.71 | 0.76 | -0.1 | -5.42 | -0.631 | -1.147 |
| Dataset C — Regime-switching (A↔B) | 0.003 | 1.91 | 0.153 | 30 | 3.96 | 63.33 | 1.44 | 0.134 | -4.0 | 1.078 | 1.814 |

**Nota**: estos resultados son sobre precios SINTÉTICOS — sirven para ver si la estrategia es frágil ante colas pesadas / criticidad auto-organizada, no como estimación de rentabilidad real.
