"""Perfiles de análisis persistentes y seguros."""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict

@dataclass
class AnalysisProfile:
    name: str
    timeframe: str = '1h'
    bars: int = 500
    min_confidence: float = 70.0
    risk_pct: float = 1.0
    market_type: str = 'spot'

BUILTIN = {
    'Conservador': AnalysisProfile('Conservador', '4h', 500, 78, .5, 'spot'),
    'Moderado': AnalysisProfile('Moderado', '1h', 500, 70, 1.0, 'spot'),
    'Agresivo': AnalysisProfile('Agresivo', '15m', 500, 64, 1.25, 'futures'),
    'Swing': AnalysisProfile('Swing', '4h', 800, 74, .75, 'spot'),
}

class ProfileManager:
    def __init__(self, path: str):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
    def load(self) -> Dict[str, AnalysisProfile]:
        profiles = dict(BUILTIN)
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding='utf-8'))
                for name, values in raw.items(): profiles[name] = AnalysisProfile(name=name, **{k:v for k,v in values.items() if k != 'name'})
            except Exception: pass
        return profiles
    def save(self, profile: AnalysisProfile) -> None:
        custom = {}
        if self.path.exists():
            try: custom = json.loads(self.path.read_text(encoding='utf-8'))
            except Exception: custom = {}
        custom[profile.name] = asdict(profile)
        self.path.write_text(json.dumps(custom, indent=2, ensure_ascii=False), encoding='utf-8')
