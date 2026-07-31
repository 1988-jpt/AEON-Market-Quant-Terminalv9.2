"""Componentes visuales futuristas reutilizables para Kivy."""
from __future__ import annotations
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

COLORS = {
    'bg': (0.018, 0.035, 0.075, 1),
    'panel': (0.028, 0.070, 0.125, 0.96),
    'panel_alt': (0.040, 0.090, 0.155, 0.96),
    'cyan': (0.00, 0.78, 0.95, 1),
    'blue': (0.18, 0.42, 1.0, 1),
    'purple': (0.56, 0.24, 1.0, 1),
    'green': (0.00, 0.86, 0.52, 1),
    'red': (1.00, 0.20, 0.38, 1),
    'amber': (1.00, 0.68, 0.10, 1),
    'text': (0.90, 0.95, 1.00, 1),
    'muted': (0.52, 0.64, 0.76, 1),
    'border': (0.05, 0.40, 0.68, 0.55),
}

class NeonPanel(BoxLayout):
    def __init__(self, radius=14, glow='border', **kwargs):
        super().__init__(**kwargs)
        self.radius = dp(radius)
        self.glow = COLORS.get(glow, COLORS['border'])
        with self.canvas.before:
            self._bg_color = Color(*COLORS['panel'])
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
            self._line_color = Color(*self.glow)
            self._line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, self.radius), width=1.1)
        self.bind(pos=self._sync_canvas, size=self._sync_canvas)
    def _sync_canvas(self, *_):
        self._bg.pos = self.pos; self._bg.size = self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, self.radius)

class MetricCard(NeonPanel):
    def __init__(self, title, value='—', detail='', accent='cyan', **kwargs):
        kwargs.setdefault('orientation', 'vertical'); kwargs.setdefault('padding', dp(12)); kwargs.setdefault('spacing', dp(2))
        kwargs.setdefault('glow', accent)
        super().__init__(**kwargs)
        self.title_label = Label(text=title.upper(), color=COLORS['muted'], font_size=dp(11), halign='left', valign='middle', size_hint_y=.28)
        self.value_label = Label(text=value, color=COLORS.get(accent, COLORS['cyan']), font_size=dp(22), bold=True, halign='left', valign='middle', size_hint_y=.46)
        self.detail_label = Label(text=detail, color=COLORS['muted'], font_size=dp(10), halign='left', valign='middle', size_hint_y=.26)
        for item in (self.title_label, self.value_label, self.detail_label):
            item.bind(size=lambda obj, val: setattr(obj, 'text_size', val)); self.add_widget(item)
    def set(self, value, detail=None, accent=None):
        self.value_label.text = str(value)
        if detail is not None: self.detail_label.text = str(detail)
        if accent: self.value_label.color = COLORS.get(accent, COLORS['cyan'])

class NeonButton(Button):
    def __init__(self, accent='cyan', **kwargs):
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_down', '')
        kwargs.setdefault('background_color', COLORS.get(accent, COLORS['cyan']))
        kwargs.setdefault('color', (0.01, 0.04, 0.08, 1))
        kwargs.setdefault('bold', True)
        super().__init__(**kwargs)

class NavButton(Button):
    def __init__(self, **kwargs):
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_color', (0,0,0,0))
        kwargs.setdefault('color', COLORS['muted'])
        kwargs.setdefault('halign', 'left')
        super().__init__(**kwargs)
        self.bind(size=lambda obj, val: setattr(obj, 'text_size', (val[0]-dp(18), val[1])))
    def set_active(self, active: bool):
        self.background_color = (0.02, .34, .56, .48) if active else (0,0,0,0)
        self.color = COLORS['cyan'] if active else COLORS['muted']
