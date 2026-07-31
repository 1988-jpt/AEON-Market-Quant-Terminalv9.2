# Mejoras de precisión sin inteligencia artificial

Esta versión mantiene la arquitectura del proyecto y añade un motor técnico más selectivo.

## Nuevos filtros
- Régimen: tendencia alcista, bajista, lateral o transición.
- Volatilidad: baja, normal, alta o extrema.
- Confirmación de temporalidad superior.
- Volumen relativo y z-score de volumen.
- Tendencia del OBV.
- Eficiencia del movimiento para evitar ruido.
- Divergencias aproximadas entre precio y RSI.
- Aceleración y cruces reales de MACD.
- Bloqueo de señales con evidencia contradictoria.
- Bloqueo de señales con volumen insuficiente o volatilidad extrema.

## Gestión de riesgo
Cuando existe una señal válida se sugieren entrada, stop-loss y dos take-profit usando ATR y niveles estructurales. Son referencias analíticas, no órdenes automáticas.

## Importante
La estrategia emitirá más resultados HOLD. Esto es intencional: intenta elevar la calidad media de las señales reduciendo operaciones débiles. El porcentaje de acierto real solo puede conocerse mediante backtesting y pruebas fuera de muestra.
