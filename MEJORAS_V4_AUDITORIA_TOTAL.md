# AΞON Market Quant Terminal V4 — auditoría y endurecimiento

## Correcciones confirmadas

- Cliente Binance público ligero predeterminado; CCXT queda opcional.
- Validación estricta de OHLCV y mínimo de datos antes del análisis.
- Esquema SQLite V4 con paper trading persistente y restricción de una posición abierta por símbolo.
- Eliminación de dependencias Android innecesarias (`ccxt`, `cryptography`).
- Navegación sin símbolos Unicode problemáticos en Windows.
- Los fallos de paper trading y actualización quedan registrados en `app.log`.

## Gestión de operaciones avanzada

El backtester incorpora:

- salida parcial configurable;
- movimiento a break-even después del parcial;
- trailing stop basado en ATR;
- límite de pérdida diaria;
- bloqueo por racha de pérdidas;
- prohibición automática de cortos en spot;
- validación geométrica de velas OHLCV.

## Validación estadística

Cada backtest añade:

- calibración empírica por rangos de calidad técnica;
- Monte Carlo reproducible;
- capital final en percentiles 5/50/95;
- drawdown P50/P95;
- riesgo de ruina aproximado;
- racha máxima de pérdidas;
- número de operaciones con salida parcial.

## Paper trading

La nueva pantalla permite abrir una operación simulada desde la señal actual,
actualizarla con nuevos análisis y cerrarla manualmente. Nunca envía órdenes a Binance.

## Alcance honesto

Esta versión mejora la ingeniería y la evaluación, pero ningún programa de trading
puede considerarse literalmente 10/10 ni garantizar beneficios. Aún deben hacerse
pruebas prolongadas en datos reales, dispositivos Android y condiciones de red adversas.
