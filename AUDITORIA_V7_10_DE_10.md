# Auditoría técnica V7 — AEON Market Quant Terminal

## Resultado de validación

- 71 módulos Python inspeccionados mediante AST.
- Compilación completa: correcta.
- Pruebas automatizadas: 36 aprobadas, 1 omitida por dependencia/plataforma.
- Sin funciones o clases de nivel superior duplicadas.
- Sin bloques `except:` desnudos.
- La importación visual completa no se ejecutó en el entorno de auditoría porque Kivy no está instalado; el código sí fue compilado correctamente y conserva sus pruebas visuales originales.

## Mejoras implementadas

1. Panel ampliado a seis tarjetas: señal, precio, calidad, sentimiento, riesgo y cuenta regresiva.
2. Balance visual de evidencia compradora/vendedora mediante normalización explicable. No se presenta como probabilidad garantizada.
3. Riesgo clasificado en BAJO, MEDIO, ALTO o MUY ALTO usando ATR relativo, volatilidad, advertencias y calidad técnica.
4. Plan operativo visible con entrada, stop loss, TP1 y TP2.
5. Estadísticas verificables de paper trading: operaciones cerradas, tasa de acierto y PnL neto.
6. Cuenta regresiva para el próximo análisis automático en modo en vivo.
7. Caché de noticias de cinco minutos para reducir latencia, consumo de red y bloqueos innecesarios.
8. SQLite optimizado con `busy_timeout`, `synchronous=NORMAL`, WAL y almacenamiento temporal en memoria.
9. Corrección de asignación duplicada del símbolo al cerrar posiciones paper.
10. Nuevo módulo aislado `decision_metrics.py` con pruebas unitarias.

## Observaciones importantes

- La calidad técnica y el balance de evidencia son indicadores internos; no garantizan resultados futuros.
- La precisión mostrada procede exclusivamente de operaciones paper cerradas, evitando presentar una precisión inventada.
- Para una validación final visual debe instalarse el entorno de `requirements.txt` y ejecutar `python test_kivy_visual.py` y `python main.py` en Windows.
