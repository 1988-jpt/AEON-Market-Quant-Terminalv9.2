[app]
title = AEON Market Quant Terminal
package.name = aeonquant
package.domain = com.aeonquant
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,json,txt,atlas,ttf
source.exclude_dirs = .venv,venv,__pycache__,tests,.pytest_cache,.git,.github,.vscode,bin,.buildozer,backtests,exports,logs,docs
source.exclude_patterns = test_*.py,run_mock.py,v5_cli.py,inspect_db.py,*.md,requirements*.txt,.env*,*.sqlite,*.sqlite3,*.db
version = 9.2.0
requirements = python3,kivy==2.3.1,numpy,requests==2.32.4,tenacity==9.1.2,websockets==13.1,plyer==2.1.0
orientation = portrait
fullscreen = 0

# Permisos mínimos para análisis de mercado y notificaciones locales.
android.permissions = INTERNET,POST_NOTIFICATIONS
android.api = 35
android.minapi = 24
android.ndk_api = 24
android.archs = arm64-v8a
android.accept_sdk_license = True

# Compilación de prueba estable: el servicio de fondo queda desactivado.
# Se puede activar después de validar la APK principal.
# services = aeonmonitor:android_service/main.py:foreground

[buildozer]
log_level = 2
warn_on_root = 0
