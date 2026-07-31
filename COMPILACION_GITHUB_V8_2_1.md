# AEON Market Quant Terminal 8.2.1

## Compilación APK en GitHub

1. Sube el contenido completo de esta carpeta al repositorio.
2. Confirma que exista `.github/workflows/build-apk.yml`.
3. En GitHub abre **Actions**.
4. Selecciona **Compilar APK AEON Mobile Pro**.
5. Pulsa **Run workflow** sobre la rama `main`.
6. Cuando termine en verde, descarga el artefacto `AEON-Mobile-Pro-APK-Debug`.

## Correcciones incluidas

- Java 17 forzado para Gradle.
- Eliminación del comando `yes`, que causaba un falso error `Broken pipe`.
- Dependencias de validación incluidas, entre ellas NumPy.
- Verificación automática de que el APK exista antes de subirlo.
- Registro de compilación disponible como artefacto.
- Orientación Android válida configurada en `portrait`.
- Caché Buildozer/Gradle renovada.
