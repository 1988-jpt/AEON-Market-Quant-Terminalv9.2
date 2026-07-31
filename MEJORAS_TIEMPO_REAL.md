# Mejoras de la versión 1.1.0

- Nuevo `realtime_feed.py`: WebSocket público de Binance, ping y reconexión exponencial.
- Nuevo `interactive_chart.py`: velas nativas Kivy con zoom, desplazamiento, cursor, EMA y niveles.
- Integración segura con la interfaz mediante `Clock`, sin bloquear el hilo gráfico.
- Actualización del precio y de indicadores durante la vela activa.
- Reanálisis completo al cierre de cada vela.
- Botón para activar/detener el tiempo real y estado visible de conexión.
- Diseño adaptable para escritorio y pantallas móviles estrechas.
- Cierre ordenado del WebSocket al salir de la aplicación.
