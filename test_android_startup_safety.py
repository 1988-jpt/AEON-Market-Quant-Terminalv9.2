from pathlib import Path
import logging

from android_runtime_guard import write_crash_report
from logging_config import setup_logging


def test_logging_survives_unwritable_target(tmp_path):
    blocker = tmp_path / "not_a_directory"
    blocker.write_text("x", encoding="utf-8")
    setup_logging(str(blocker / "app.log"), force=True)
    logging.getLogger("test").info("still alive")


def test_crash_report_is_written(tmp_path):
    try:
        raise RuntimeError("startup-test")
    except RuntimeError as exc:
        path = write_crash_report(exc, tmp_path)
    assert path is not None
    assert path.exists()
    assert "startup-test" in path.read_text(encoding="utf-8")


def test_android_main_does_not_log_before_app_dir():
    source = Path("main.py").read_text(encoding="utf-8")
    android_block = source.split("if _is_android():", 1)[1].split("return", 1)[0]
    assert "setup_logging" not in android_block
