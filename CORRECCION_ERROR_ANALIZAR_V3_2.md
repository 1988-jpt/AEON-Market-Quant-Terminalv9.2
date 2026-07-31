# Corrección V3.2: error al pulsar ANALIZAR

## Causa principal
Versiones anteriores creaban `signals` con `UNIQUE(ts, symbol, signal)`. La versión V3 intentaba guardar con `ON CONFLICT(ts, symbol)`. SQLite no modifica restricciones de una tabla existente cuando se usa `CREATE TABLE IF NOT EXISTS`, por lo que instalaciones actualizadas conservaban el esquema anterior y el guardado final fallaba.

## Solución
- Migración automática y segura de la tabla `signals`.
- Conservación de la fila más reciente por vela y símbolo.
- Nueva versión de esquema guardada en `metadata`.
- Registro completo de excepciones en `app.log`.
- El detalle del error ahora aparece en el Dashboard, no solo en otra pantalla.

No es necesario borrar manualmente la base de datos.
