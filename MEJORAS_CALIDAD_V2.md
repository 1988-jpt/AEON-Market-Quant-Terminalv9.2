# Mejoras de calidad v2

- Credenciales eliminadas de la plantilla `.env`.
- Configuración validada y valores seguros.
- Descarga histórica paginada mediante `since` y bloques de hasta 1.000 velas.
- Confirmación multi-timeframe dentro del backtesting.
- Equity mark-to-market en cada vela.
- Gaps de apertura ejecutados al precio disponible, no al stop ideal.
- Comisión, spread y slippage separados.
- Sharpe y Sortino anualizados según la temporalidad y mercado 24/7.
- Walk-forward real con varias ventanas móviles.
- Persistencia de ejecuciones y operaciones en SQLite.
- Reportes versionados con fecha UTC y hash de configuración.
- Parámetros editables desde la pestaña Backtesting.
- Validación de temporalidades en WebSocket.
- 10 pruebas automáticas sobre los comportamientos críticos.

## Límites conscientes

- El modo spot desactiva cortos; el modo futures los permite como simulación.
- Funding, profundidad del libro e impacto de mercado no se modelan todavía.
- Matplotlib es opcional en Android; JSON y CSV siguen disponibles.
