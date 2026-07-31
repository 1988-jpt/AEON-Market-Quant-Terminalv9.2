# AEON Market Quant Terminal V8 Professional

## Resultado de auditoría

- Compilación completa de todos los módulos Python: correcta.
- Pruebas automatizadas: **39 aprobadas, 1 omitida** por dependencia visual de Kivy.
- Ejecución real: Testnet por defecto; Mainnet permanece bloqueado salvo activación deliberada.
- Credenciales: se mantienen fuera del código mediante variables de entorno.

## Mejoras de esta versión

### Rendimiento
- Nueva caché TTL thread-safe y con límite LRU (`performance_cache.py`).
- Evita cálculos o consultas repetidos y expone tasa de aciertos de caché.
- Mantiene las optimizaciones previas de SQLite WAL, caché de noticias y runtime asíncrono.

### Seguridad operativa
- Nuevo módulo centralizado `operational_guardrails.py`.
- Lista blanca de símbolos.
- Límite de valor por orden.
- Límite de pérdida diaria.
- Máximo de órdenes abiertas.
- Bloqueo de órdenes duplicadas por identificador.
- Reinicio automático del contador diario en UTC.
- Frase de confirmación separada para Testnet y Mainnet.

### Motor de ejecución
- Validación estricta de respuestas del exchange.
- Timeout configurable.
- Identificadores de cliente limitados a 36 caracteres.
- Mainnet sigue deshabilitado por defecto.
- Registro explícito de PnL realizado para aplicar el límite diario.

### Interfaz y producto
- Identidad visual actualizada a **QUANT TERMINAL V8 PRO**.
- APK renombrado a **AEON Market Quant Terminal**.
- Paquete Android actualizado a `com.aeonquant.aeonquant`.
- Versión Android: `8.0.0`.
- Las métricas ahora distinguen claramente evidencia técnica de probabilidad estadística.

## Archivos nuevos

- `operational_guardrails.py`
- `performance_cache.py`
- `VERSION.py`
- `test_v8_guardrails_performance.py`

## Limitaciones honestas

La compilación y las pruebas garantizan consistencia lógica y sintáctica en este entorno. La interfaz Kivy y la generación final del APK deben probarse en Windows/Linux con Kivy y Buildozer instalados, y luego en un dispositivo Android real. Ningún sistema de trading puede garantizar ganancias ni ausencia absoluta de errores bajo todos los escenarios de red o exchange.
