"""Auditoría determinista antes de enviar AEON a Buildozer."""
from __future__ import annotations

import ast
import configparser
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
errors: list[str] = []
warnings: list[str] = []

REQUIRED_FILES = (
    "main.py",
    "mobile_app.py",
    "android_bootstrap_app.py",
    "android_runtime_guard.py",
    "android_analyzer_service.py",
    "mobile_market_core.py",
    "binance_rest_client.py",
    "requirements-android.txt",
    "buildozer.spec",
    ".github/workflows/build-apk.yml",
)

for required in REQUIRED_FILES:
    if not (ROOT / required).is_file():
        errors.append(f"Falta {required}")

# Sintaxis completa, sin depender de imports instalados en el runner.
for path in ROOT.rglob("*.py"):
    if any(part in {".venv", "venv", ".buildozer", "__pycache__", ".pytest_cache"} for part in path.parts):
        continue
    try:
        ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    except Exception as exc:
        errors.append(f"Error de sintaxis en {path.relative_to(ROOT)}: {exc}")

spec = configparser.ConfigParser(interpolation=None)
spec_path = ROOT / "buildozer.spec"
if spec_path.is_file():
    spec.read(spec_path, encoding="utf-8")

if "app" not in spec:
    errors.append("buildozer.spec no contiene [app]")
else:
    app = spec["app"]
    mandatory = (
        "title", "package.name", "package.domain", "version", "requirements",
        "android.api", "android.minapi", "android.ndk_api", "android.archs",
    )
    for key in mandatory:
        if not app.get(key, "").strip():
            errors.append(f"Falta {key} en buildozer.spec")

    raw_requirements = [item.strip() for item in app.get("requirements", "").split(",") if item.strip()]
    requirement_names = {
        re.split(r"[<>=!~]", item, maxsplit=1)[0].strip().lower().replace("_", "-")
        for item in raw_requirements
    }
    forbidden = {"python-dotenv", "pandas", "matplotlib", "scipy", "tensorflow", "torch", "ccxt"}
    bad = sorted(requirement_names & forbidden)
    if bad:
        errors.append("Dependencias Android no recomendadas: " + ", ".join(bad))

    required_mobile = {"python3", "kivy", "numpy", "requests", "websockets", "plyer"}
    missing_mobile = sorted(required_mobile - requirement_names)
    if missing_mobile:
        errors.append("Dependencias Android obligatorias ausentes: " + ", ".join(missing_mobile))


    # requirements-android.txt debe reflejar exactamente las dependencias
    # directas de buildozer.spec para impedir conflictos silenciosos.
    req_file = ROOT / "requirements-android.txt"
    if req_file.is_file():
        android_lines = [
            line.strip() for line in req_file.read_text(encoding="utf-8-sig").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        normalized_android = [
            re.split(r"[<>=!~]", item, maxsplit=1)[0].strip().lower().replace("_", "-")
            for item in android_lines
        ]
        duplicates = sorted({name for name in normalized_android if normalized_android.count(name) > 1})
        if duplicates:
            errors.append("Dependencias duplicadas en requirements-android.txt: " + ", ".join(duplicates))
        android_names = set(normalized_android)
        if android_names != requirement_names:
            missing_in_file = sorted(requirement_names - android_names)
            extra_in_file = sorted(android_names - requirement_names)
            if missing_in_file:
                errors.append("Faltan en requirements-android.txt: " + ", ".join(missing_in_file))
            if extra_in_file:
                errors.append("Sobran en requirements-android.txt: " + ", ".join(extra_in_file))

    if app.get("android.archs", "").strip() != "arm64-v8a":
        warnings.append("android.archs no está limitado a arm64-v8a")
    try:
        if int(app.get("android.minapi", "0")) < 24:
            errors.append("android.minapi debe ser 24 o superior")
    except ValueError:
        errors.append("android.minapi no es un número válido")

# Los módulos importados al iniciar Android no pueden depender directamente de paquetes pesados.
android_startup_modules = {
    "main.py",
    "android_bootstrap_app.py",
    "mobile_app.py",
    "android_analyzer_service.py",
    "mobile_market_core.py",
    "binance_client.py",
    "binance_rest_client.py",
    "interactive_chart.py",
    "market_scanner.py",
    "profile_manager.py",
    "paper_trading.py",
    "paper_monitor.py",
    "realtime_feed.py",
    "candle_recovery.py",
    "native_notifications.py",
    "signal_explainer.py",
    "decision_metrics.py",
    "storage.py",
    "system_diagnostics.py",
    "ui_theme.py",
    "async_runtime.py",
    "platform_runtime.py",
    "logging_config.py",
    "config.py",
}
forbidden_imports = {"dotenv", "pandas", "matplotlib", "scipy", "tensorflow", "torch", "ccxt"}
for filename in sorted(android_startup_modules):
    path = ROOT / filename
    if not path.is_file():
        errors.append(f"Módulo de inicio Android ausente: {filename}")
        continue
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=filename)
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module.split(".")[0]]
        for name in names:
            # CCXT es una dependencia opcional cargada dentro de _get_client;
            # Android usa el backend REST público y nunca ejecuta ese import.
            if filename == "binance_client.py" and name == "ccxt":
                continue
            # interactive_chart conserva un fallback opcional para escritorio;
            # Android usa CandleSeries y no necesita Pandas.
            if filename == "interactive_chart.py" and name == "pandas":
                continue
            if name in forbidden_imports:
                errors.append(f"Import Android incompatible en {filename}: {name}")

main_source = (ROOT / "main.py").read_text(encoding="utf-8-sig") if (ROOT / "main.py").is_file() else ""
if "AndroidBootstrapApp" not in main_source:
    errors.append("main.py no utiliza AndroidBootstrapApp")

bootstrap_source = (ROOT / "android_bootstrap_app.py").read_text(encoding="utf-8-sig") if (ROOT / "android_bootstrap_app.py").is_file() else ""
if 'importlib.import_module("mobile_app")' not in bootstrap_source:
    errors.append("android_bootstrap_app.py no realiza carga tardía de mobile_app")
if "write_crash_report" not in bootstrap_source:
    errors.append("android_bootstrap_app.py no registra fallos de arranque")

version_file = ROOT / "VERSION.py"
if version_file.is_file() and "app" in spec:
    match = re.search(r'VERSION\s*=\s*["\']([^"\']+)', version_file.read_text(encoding="utf-8"))
    file_version = match.group(1) if match else ""
    spec_version = spec["app"].get("version", "").strip()
    if not file_version:
        errors.append("VERSION.py no contiene una versión válida")
    elif file_version != spec_version:
        errors.append(f"Versión inconsistente: VERSION.py={file_version}, buildozer.spec={spec_version}")

if warnings:
    print("PRECHECK APK: ADVERTENCIAS")
    for warning in warnings:
        print(" -", warning)

if errors:
    print("PRECHECK APK: FALLÓ")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("PRECHECK APK: OK")
print("Proyecto Android consistente y listo para Buildozer.")
