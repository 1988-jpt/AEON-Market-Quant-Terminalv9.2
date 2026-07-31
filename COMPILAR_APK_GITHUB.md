# Compilar la APK con GitHub Actions

1. Crea un repositorio en GitHub y sube **el contenido de esta carpeta**.
2. Comprueba que `main.py`, `buildozer.spec` y `.github/workflows/build-apk.yml` estén en la raíz.
3. Abre la pestaña **Actions**.
4. Selecciona **Compilar APK AEON**.
5. Pulsa **Run workflow** y confirma.
6. Al terminar, abre la ejecución y descarga el artefacto **AEON-V8-APK-Debug**.
7. Descomprime el artefacto e instala el archivo `.apk` en Android.

La primera compilación puede tardar bastante porque GitHub descarga el SDK, NDK y Gradle.

## Si falla

Abre el paso rojo **Generar APK debug** y copia desde la primera línea que contenga `ERROR:` hasta el final. También se subirá el artefacto `AEON-Build-Logs` cuando existan registros.
