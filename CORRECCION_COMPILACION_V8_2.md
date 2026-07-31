# AEON Market Quant Terminal V8.2 Mobile Pro

## Corrección principal

La compilación anterior llegó hasta Gradle, pero falló porque Android Gradle Plugin requería Java 17 y el proceso estaba usando Java 11.

El workflow nuevo:

- instala y selecciona Temurin Java 17 con `actions/setup-java@v4`;
- verifica explícitamente `java` y `javac` antes de compilar;
- fuerza `JAVA_HOME`, `PATH`, `GRADLE_OPTS` y `org.gradle.java.home`;
- localiza automáticamente `buildozer.spec`, aunque el proyecto haya quedado dentro de una carpeta;
- conserva cachés separadas para Java 17;
- guarda el registro completo `buildozer-full.log` cuando hay un fallo;
- sube el APK como artefacto `AEON-Mobile-Pro-APK-Debug`.

## Uso en GitHub

Sube el contenido completo del proyecto y reemplaza el archivo:

`.github/workflows/build-apk.yml`

Después ejecuta:

`Actions > Compilar APK AEON Mobile Pro > Run workflow`

La advertencia de deprecación de Node.js mostrada por GitHub no era la causa del fallo.
