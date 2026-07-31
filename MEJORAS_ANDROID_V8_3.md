# AEON V8.3 Android Safe Start

## Cambios principales

- El logging ya no intenta escribir antes de conocer el directorio privado Android.
- Un fallo al crear `app.log` nunca cierra la aplicación.
- Pantalla de arranque ligera antes de construir los servicios pesados.
- Captura global de excepciones y archivo `aeon_startup_crash.log`.
- Botón de reintento si falla la construcción del Dashboard.
- Solicitud segura únicamente de `POST_NOTIFICATIONS`.
- Cierre defensivo de WebSocket, tareas asíncronas y servicio.
- Nuevas pruebas de seguridad de arranque.
- Workflow de GitHub actualizado para ejecutar todos los `test_*.py`.

## Nota

Ningún software puede garantizar cero errores en todos los modelos Android. Esta versión evita los cierres silenciosos más comunes y conserva un diagnóstico local cuando ocurre una excepción.
