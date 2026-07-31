"""Caché local rápida y segura para históricos públicos."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Optional
import json, os, time
import pandas as pd

@dataclass
class CachePolicy:
    live_ttl_seconds: int = 300
    dated_ttl_seconds: int = 7 * 24 * 3600
    max_files: int = 80

class HistoricalCache:
    def __init__(self, directory: Optional[str], policy: Optional[CachePolicy] = None):
        self.directory = Path(directory) if directory else None
        self.policy = policy or CachePolicy()
        if self.directory:
            self.directory.mkdir(parents=True, exist_ok=True)

    def _paths(self, key: dict):
        digest = sha256(json.dumps(key, sort_keys=True, default=str).encode()).hexdigest()[:20]
        return self.directory / f"{digest}.pkl", self.directory / f"{digest}.json"

    def get(self, key: dict, dated: bool = False) -> Optional[pd.DataFrame]:
        if not self.directory:
            return None
        data_path, meta_path = self._paths(key)
        if not data_path.exists() or not meta_path.exists():
            return None
        ttl = self.policy.dated_ttl_seconds if dated else self.policy.live_ttl_seconds
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if time.time() - float(meta["created_at"]) > ttl:
                return None
            frame = pd.read_pickle(data_path)
            return frame if not frame.empty else None
        except Exception:
            return None

    def put(self, key: dict, frame: pd.DataFrame) -> None:
        if not self.directory or frame is None or frame.empty:
            return
        data_path, meta_path = self._paths(key)
        tmp = data_path.with_suffix(".tmp")
        frame.to_pickle(tmp)
        os.replace(tmp, data_path)
        meta_path.write_text(json.dumps({"created_at": time.time(), "rows": len(frame)}), encoding="utf-8")
        self.prune()

    def prune(self) -> None:
        if not self.directory:
            return
        files = sorted(self.directory.glob("*.pkl"), key=lambda p: p.stat().st_mtime, reverse=True)
        for path in files[self.policy.max_files:]:
            try:
                path.unlink(missing_ok=True)
                path.with_suffix(".json").unlink(missing_ok=True)
            except OSError:
                pass
