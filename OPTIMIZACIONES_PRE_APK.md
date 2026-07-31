# Optimización de rendimiento y calidad pre-APK

## Cambios principales
- Arranque ligero: imports pesados diferidos en `main.py` y `binance_client.py`.
- Cliente Binance persistente dentro del servicio para no recrear mercados/conexiones en cada análisis.
- Descarga de velas, noticias y temporalidad superior en paralelo.
- Indicadores precalculados una sola vez durante backtesting.
- Caché binaria local de históricos con TTL y poda automática.
- Gráfico limitado a 30 redibujados por segundo y recorrido de velas optimizado.
- Pausa Android: el tiempo real se detiene al enviar la app a segundo plano.
- Nuevas pruebas de equivalencia y caché.

## Por qué acelera el programa
El motor anterior recalculaba EMA, RSI, MACD, ATR, ADX y otros indicadores sobre
todo el historial en cada vela del backtest. Ahora los calcula una sola vez y
entrega porciones causales a la estrategia. No se usan filas futuras.

## Compatibilidad
Se mantienen las firmas públicas de `AdvancedStrategy.decide`,
`BacktestEngine.run`, `BacktestService.run` y `MarketAnalyzerService.analyze`.
