# AEON V9.1.1 — Auditoría y corrección Android

## Causa raíz confirmada

La compilación fallaba porque python-for-android resolvía su receta de `python-dotenv` como 1.2.2, mientras `buildozer.spec` solicitaba 1.1.1. El requirements temporal terminaba incluyendo ambas versiones y Pip abortaba con `ResolutionImpossible`.

## Correcciones aplicadas

1. Se retiró `python-dotenv` de la APK, del workflow y de los requirements del proyecto.
2. `config.py` ahora incluye un lector `.env` interno y tolerante, sin dependencia externa.
3. `buildozer.spec` contiene solo dependencias Android directas. Las dependencias transitivas de Requests ya no se duplican manualmente.
4. `requirements-android.txt` quedó sincronizado exactamente con `buildozer.spec`.
5. `apk_preflight.py` detecta dependencias prohibidas, duplicadas o inconsistentes entre ambos archivos.
6. El workflow elimina requirements temporales obsoletos antes de compilar para impedir que una caché antigua reactive el conflicto.
7. La versión se actualizó a 9.1.1.

## Validaciones ejecutadas

- Preflight Android: OK
- Compilación sintáctica de todos los módulos: OK
- YAML del workflow: OK
- Pruebas completas: 42 aprobadas, 1 omitida

## Dependencias Android finales

- python3
- kivy==2.3.1
- numpy
- requests==2.32.4
- tenacity==9.1.2
- websockets==13.1
- plyer==2.1.0

## Nota

Estas validaciones eliminan el error reproducible del log y los conflictos estáticos detectados. La garantía definitiva requiere ejecutar GitHub Actions, porque el SDK/NDK y python-for-android se descargan y compilan en el runner remoto.
