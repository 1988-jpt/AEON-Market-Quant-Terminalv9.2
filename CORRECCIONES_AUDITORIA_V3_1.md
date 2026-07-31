# Auditoría y correcciones V3.1

## Incidencias confirmadas por el registro de ejecución

1. **Advertencia de tamaño mínimo de Kivy**
   - Causa: `Window.minimum_width` y `Window.minimum_height` se asignaban por separado después de inicializar la ventana.
   - Corrección: configuración conjunta antes de importar/inicializar la ventana mediante `kivy.config.Config`.

2. **Conexión WebSocket terminando después de cerrar la aplicación**
   - Síntoma: aparecía `Tiempo real: Conectado` después de `Leaving application in progress...`.
   - Causa: `stop()` solo marcaba un evento, pero no cerraba inmediatamente el socket ni esperaba al hilo.
   - Corrección: cierre explícito del WebSocket, espera limitada del hilo y bloqueo de callbacks durante el apagado.

3. **Riesgo de conexiones en tiempo real duplicadas**
   - Causa: al iniciar, `realtime_feed` todavía podía ser `None` durante unos milisegundos y un segundo clic iniciaba otro hilo.
   - Corrección: estado explícito `realtime_active` desde antes de crear el hilo.

4. **Uso de varios event loops con clientes asíncronos persistentes**
   - Causa: análisis, escáner y backtesting usaban `asyncio.run()` desde hilos diferentes, aunque compartían servicios, locks y el cliente CCXT.
   - Riesgo: errores del tipo “bound to a different event loop”, sesiones HTTP inestables y cierres incompletos.
   - Corrección: nuevo `AsyncRuntime`, un único bucle asíncrono persistente para todos esos servicios.

5. **Mensajes duplicados en consola**
   - Causa: Kivy ya instala un manejador de consola y `setup_logging()` añadía otro.
   - Corrección: el logger detecta el manejador de Kivy y no agrega un segundo `StreamHandler`.

6. **Errores silenciosos del escáner**
   - Causa: las excepciones por activo se convertían en `ERROR` sin quedar registradas.
   - Corrección: se conserva el resultado `ERROR`, pero ahora se registra la causa en el log.

## Módulos revisados

- `main.py`: correcto; mantiene modo gráfico y `--once`.
- `mobile_app.py`: corregidos tamaño mínimo, runtime asíncrono, apagado y control de tiempo real.
- `realtime_feed.py`: corregido cierre inmediato y seguro del socket.
- `async_runtime.py`: nuevo módulo para estabilidad de event loops.
- `logging_config.py`: corregida duplicación de mensajes.
- `market_scanner.py`: mejorada trazabilidad de fallos.
- Estrategia, indicadores, riesgo, almacenamiento, caché, backtesting, walk-forward, perfiles y diagnóstico: sin errores funcionales detectados por compilación y pruebas actuales.

## Validación

- Compilación completa: correcta.
- Pruebas automáticas: **18 passed**.
- Nuevas pruebas: reutilización del mismo event loop, detención segura del feed y ausencia de doble consola con Kivy.

## Interpretación del registro original

Las líneas de inicialización de Kivy, SDL2, GLEW y OpenGL son informativas y no representan errores. La GPU Intel HD Graphics 510 inicializó OpenGL 4.6 correctamente. Los problemas reales eran la advertencia de tamaño mínimo y la carrera de apagado del WebSocket.
