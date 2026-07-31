# AEON V8.4 — Android Resilient Startup

## Cambios principales

- Nuevo `android_bootstrap_app.py`, una pantalla de arranque mínima que aparece antes de importar el motor completo.
- Carga tardía de `mobile_app`, evitando el cierre silencioso cuando falla un módulo opcional o una dependencia.
- Pantalla de error recuperable con botón **REINTENTAR**.
- Registro separado de fallos durante bootstrap, ejecución, hilos secundarios y errores nativos.
- Marcador `startup_state.txt` con los estados `starting`, `ready` o `failed`.
- Verificación temprana de dependencias Android esenciales y del almacenamiento privado.
- Cierre Android más corto y tolerante para reducir bloqueos al salir o pausar.
- `apk_preflight.py` ahora exige y valida la arquitectura de arranque seguro.
- Versión actualizada a `8.4.0`.

## Archivos de diagnóstico generados en Android

Dentro del almacenamiento privado de la aplicación:

- `app.log`
- `aeon_startup_crash.log`
- `aeon_native_fault.log`
- `startup_state.txt`

Para obtenerlos mediante ADB durante una prueba:

```bash
adb logcat -c
adb logcat | grep -i -E "python|aeon|kivy|AndroidRuntime"
```

## Resultado de validación

- Compilación sintáctica completa: correcta.
- Preflight APK: correcto.
- Pruebas automatizadas: 42 aprobadas, 1 omitida.
