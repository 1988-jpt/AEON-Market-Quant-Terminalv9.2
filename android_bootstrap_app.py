"""Arranque Android mínimo, visible y recuperable.

Este módulo importa únicamente componentes básicos de Kivy. La interfaz completa
se carga después de que la primera pantalla ya está visible, por lo que un fallo
de dependencia no provoca un cierre silencioso de la APK.
"""
from __future__ import annotations

import gc
import importlib
import logging
import os
import platform
import sys
import threading
import time
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.widget import Widget

logger = logging.getLogger(__name__)


class AndroidStartupView(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(24), spacing=dp(14), **kwargs)
        with self.canvas.before:
            Color(0.025, 0.035, 0.065, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        self.add_widget(Widget(size_hint_y=.22))
        self.title_label = Label(
            text="[b][color=00D9FF]AΞON[/color][/b]\nMARKET QUANT TERMINAL",
            markup=True,
            font_size=dp(25),
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=dp(105),
        )
        self.title_label.bind(size=lambda obj, value: setattr(obj, "text_size", value))
        self.add_widget(self.title_label)

        self.status_label = Label(
            text="Preparando inicio seguro…",
            font_size=dp(14),
            halign="center",
            valign="middle",
            color=(.82, .88, .98, 1),
            size_hint_y=None,
            height=dp(110),
        )
        self.status_label.bind(size=lambda obj, value: setattr(obj, "text_size", value))
        self.add_widget(self.status_label)
        self.progress = ProgressBar(max=100, value=5, size_hint_y=None, height=dp(10))
        self.add_widget(self.progress)
        self.retry_button = Button(
            text="REINTENTAR",
            size_hint_y=None,
            height=dp(50),
            opacity=0,
            disabled=True,
        )
        self.add_widget(self.retry_button)
        self.add_widget(Widget(size_hint_y=.38))

    def _sync_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def status(self, text: str, progress: int) -> None:
        self.status_label.text = text
        self.progress.value = progress

    def error(self, text: str, report_path: Path | None = None) -> None:
        suffix = f"\n\nInforme: {report_path}" if report_path else ""
        self.status_label.text = (
            "[b][color=FF6B81]AEON no pudo completar el inicio.[/color][/b]\n"
            f"{text}{suffix}"
        )
        self.status_label.markup = True
        self.progress.value = 100
        self.retry_button.opacity = 1
        self.retry_button.disabled = False


class AndroidBootstrapApp(App):
    title = "AΞON Market Quant Terminal"

    def build(self):
        Window.clearcolor = (.025, .035, .065, 1)
        self.data_dir = Path(self.user_data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        from logging_config import setup_logging
        from android_runtime_guard import enable_fault_log, install_exception_hook, install_thread_exception_hook

        setup_logging(str(self.data_dir / "app.log"), force=True)
        install_exception_hook(self.data_dir)
        install_thread_exception_hook(self.data_dir)
        enable_fault_log(self.data_dir)

        self.view = AndroidStartupView()
        self.view.retry_button.bind(on_release=lambda *_: self.start_loading())
        self.dashboard = None
        self._loading = False
        self._write_startup_marker("starting")
        return self.view

    def on_start(self):
        Clock.schedule_once(lambda _dt: self.start_loading(), .20)
        Clock.schedule_once(self._request_android_permissions, .75)

    def start_loading(self):
        if self._loading:
            return
        self._loading = True
        self.view.retry_button.disabled = True
        self.view.retry_button.opacity = 0
        self.view.status("Verificando entorno Android…", 15)
        Clock.schedule_once(self._load_runtime, .05)

    def _load_runtime(self, _dt):
        try:
            self._environment_check()
            self.view.status("Cargando motor de análisis…", 40)
            Clock.schedule_once(self._load_dashboard, .05)
        except BaseException as exc:
            self._show_failure(exc)

    def _load_dashboard(self, _dt):
        try:
            # Importación deliberadamente tardía: la pantalla segura ya existe.
            module = importlib.import_module("mobile_app")
            dashboard_cls = getattr(module, "Dashboard")
            self.view.status("Construyendo interfaz optimizada…", 70)
            dashboard = dashboard_cls(self.data_dir)
            self.dashboard = dashboard
            self.root.clear_widgets()
            self.root.add_widget(dashboard)
            self._write_startup_marker("ready")
            logger.info("Arranque Android seguro completado")
            gc.collect()
        except BaseException as exc:
            self._show_failure(exc)

    def _environment_check(self) -> None:
        required = ("kivy", "numpy", "requests", "websockets")
        missing = []
        for name in required:
            try:
                importlib.import_module(name)
            except Exception as exc:
                missing.append(f"{name}: {type(exc).__name__}: {exc}")
        if missing:
            raise RuntimeError("Dependencias no disponibles:\n" + "\n".join(missing))
        if not os.access(self.data_dir, os.W_OK):
            raise RuntimeError("El directorio privado de la aplicación no es escribible.")

    def _show_failure(self, exc: BaseException) -> None:
        self._loading = False
        logger.critical("Fallo de arranque recuperable", exc_info=(type(exc), exc, exc.__traceback__))
        report_path = None
        try:
            from android_runtime_guard import write_crash_report
            report_path = write_crash_report(exc, self.data_dir, phase="bootstrap")
        except Exception:
            logger.exception("No se pudo escribir el informe de arranque")
        message = str(exc).strip() or type(exc).__name__
        self.view.error(message[:900], report_path)
        self._write_startup_marker("failed")

    def _write_startup_marker(self, state: str) -> None:
        try:
            content = (
                f"state={state}\n"
                f"time={time.time()}\n"
                f"python={sys.version}\n"
                f"platform={platform.platform()}\n"
            )
            (self.data_dir / "startup_state.txt").write_text(content, encoding="utf-8")
        except Exception:
            pass

    def _request_android_permissions(self, _dt):
        try:
            from android.permissions import Permission, request_permissions
            permission = getattr(Permission, "POST_NOTIFICATIONS", None)
            if permission:
                request_permissions([permission])
        except Exception:
            logger.warning("No se pudo solicitar permiso de notificaciones", exc_info=True)

    def on_pause(self):
        if self.dashboard is not None:
            try:
                self.dashboard.stop_realtime(wait=False)
            except Exception:
                logger.exception("Fallo al pausar tiempo real")
        return True

    def on_stop(self):
        dashboard = self.dashboard
        if dashboard is None:
            return
        try:
            dashboard.shutting_down = True
            dashboard.stop_realtime(wait=False, update_ui=False)
            for future in list(getattr(dashboard, "_async_futures", ())):
                future.cancel()
            runtime = getattr(dashboard, "async_runtime", None)
            service = getattr(dashboard, "service", None)
            if runtime is not None and service is not None:
                close_result = service.close()
                if hasattr(close_result, "__await__"):
                    try:
                        runtime.submit(close_result).result(timeout=3)
                    except Exception:
                        logger.warning("Cierre asíncrono incompleto", exc_info=True)
                runtime.shutdown(timeout=3)
        except Exception:
            logger.exception("Fallo durante cierre controlado")
