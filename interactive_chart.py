"""Gráfico interactivo nativo de Kivy para escritorio y Android."""

from __future__ import annotations

from typing import Dict, Optional

try:
    import pandas as pd
except ImportError:
    pd = None
from kivy.graphics import Color, Line, Rectangle
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import NumericProperty, ObjectProperty
from kivy.uix.widget import Widget


class InteractiveMarketChart(Widget):
    """Velas con zoom, desplazamiento y cursor de inspección."""

    zoom = NumericProperty(1.0)
    pan = NumericProperty(0.0)
    frame = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.levels: Dict = {}
        self.symbol = ''
        self.crosshair: Optional[tuple] = None
        self._touch_start_x = None
        self._redraw_trigger = Clock.create_trigger(self.redraw, 1/30)
        self.bind(pos=self.schedule_redraw, size=self.schedule_redraw,
                  zoom=self.schedule_redraw, pan=self.schedule_redraw)

    def set_data(self, dataframe, levels: Optional[Dict] = None,
                 symbol: str = '') -> None:
        self.frame = dataframe.copy() if dataframe is not None else None
        self.levels = levels or {}
        self.symbol = symbol
        self.pan = 0
        self.schedule_redraw()

    def schedule_redraw(self, *_):
        self._redraw_trigger()

    def update_last_candle(self, timestamp_ms: int, values: Dict[str, float]) -> None:
        if self.frame is None or getattr(self.frame, 'empty', False): return
        if hasattr(self.frame, 'rows'):
            rows=self.frame.rows
            found=False
            for row in reversed(rows):
                if int(row.get('timestamp_ms',-1))==int(timestamp_ms): row.update(values); found=True; break
            if not found:
                item={'timestamp_ms':int(timestamp_ms),**values}; rows.append(item); rows.sort(key=lambda r:r['timestamp_ms']); self.frame.rows=rows[-700:]
        else:
            if pd is None:
                raise RuntimeError(
                    'El gráfico recibió un DataFrame de Pandas en Android, pero Pandas no está disponible. '
                    'Use MobileFrame/rows para la interfaz móvil.'
                )
            timestamp = pd.to_datetime(timestamp_ms, unit='ms', utc=True)
            if self.frame.index.tz is None: timestamp = timestamp.tz_localize(None)
            if timestamp in self.frame.index:
                for key,value in values.items():
                    if key in self.frame.columns:self.frame.loc[timestamp,key]=value
            else:
                new_row={column:float('nan') for column in self.frame.columns}; new_row.update(values); self.frame.loc[timestamp]=new_row; self.frame.sort_index(inplace=True); self.frame=self.frame.tail(700)
        self.schedule_redraw()

    def _visible_frame(self):
        if self.frame is None or getattr(self.frame,'empty',False): return None
        total=len(self.frame); base=90; count=max(20,min(total,int(base/max(self.zoom,.35)))); max_pan=max(0,total-count); pan=int(max(0,min(max_pan,self.pan))); end=total-pan; start=max(0,end-count)
        if hasattr(self.frame,'rows'): return self.frame.rows[start:end]
        return self.frame.iloc[start:end]

    def reset_view(self) -> None:
        self.zoom = 1.0
        self.pan = 0
        self.crosshair = None
        self.schedule_redraw()

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if touch.is_mouse_scrolling:
            self.zoom = min(4.0, self.zoom * 1.15) if touch.button == 'scrollup' else max(.35, self.zoom / 1.15)
            return True
        self._touch_start_x = touch.x
        self.crosshair = touch.pos
        self.schedule_redraw()
        return True

    def on_touch_move(self, touch):
        if self._touch_start_x is None or not self.collide_point(*touch.pos):
            return super().on_touch_move(touch)
        delta = touch.x - self._touch_start_x
        if abs(delta) > dp(5):
            visible = self._visible_frame()
            if visible is not None and len(visible):
                candles_per_px = len(visible) / max(self.width, 1)
                self.pan += -delta * candles_per_px
                self._touch_start_x = touch.x
        self.crosshair = touch.pos
        self.schedule_redraw()
        return True

    def on_touch_up(self, touch):
        self._touch_start_x = None
        if self.collide_point(*touch.pos):
            self.crosshair = touch.pos
            self.redraw()
            return True
        return super().on_touch_up(touch)

    def redraw(self, *_):
        self.canvas.clear()
        frame = self._visible_frame()
        with self.canvas:
            Color(.035, .055, .09, 1)
            Rectangle(pos=self.pos, size=self.size)
            if frame is None or (hasattr(frame,'empty') and frame.empty) or len(frame)==0 or self.width < 20 or self.height < 20:
                return

            left, bottom = self.x + dp(52), self.y + dp(26)
            right, top = self.right - dp(12), self.top - dp(28)
            chart_w, chart_h = max(1, right-left), max(1, top-bottom)
            records = frame if isinstance(frame,list) else [row._asdict() for row in frame.itertuples()]
            minimum=min(float(r['low']) for r in records); maximum=max(float(r['high']) for r in records)
            margin = max((maximum-minimum) * .08, maximum * .0005, 1e-9)
            minimum -= margin; maximum += margin

            Color(.13, .18, .26, 1)
            for n in range(6):
                y = bottom + chart_h*n/5
                Line(points=[left, y, right, y], width=.65)
            for n in range(7):
                x = left + chart_w*n/6
                Line(points=[x, bottom, x, top], width=.45)

            def py(value):
                return bottom + (float(value)-minimum)/(maximum-minimum)*chart_h

            for value in self.levels.get('supports', []):
                Color(.1, .75, .55, .75); Line(points=[left, py(value), right, py(value)], width=1, dash_length=5, dash_offset=3)
            for value in self.levels.get('resistances', []):
                Color(.95, .35, .4, .75); Line(points=[left, py(value), right, py(value)], width=1, dash_length=5, dash_offset=3)

            step = chart_w / max(len(records), 1)
            candle_w = max(1, min(dp(11), step*.62))
            for index, row in enumerate(records):
                x = left + (index+.5)*step
                rising = float(row['close']) >= float(row['open'])
                Color(.12, .83, .62, 1) if rising else Color(.97, .32, .42, 1)
                Line(points=[x, py(row['low']), x, py(row['high'])], width=1)
                y1, y2 = py(row['open']), py(row['close'])
                Rectangle(pos=(x-candle_w/2, min(y1,y2)), size=(candle_w, max(dp(1.5), abs(y2-y1))))

            overlays = [('ema_9', (.3,.65,1,1)), ('ema_21', (1,.72,.22,1)), ('ema_50', (.78,.42,1,1))]
            for column, color in overlays:
                if not records or column not in records[-1]: continue
                points=[]
                for i,row in enumerate(records):
                    value=row.get(column)
                    if value is not None and value==value: points.extend((left+(i+.5)*step,py(value)))
                if len(points) >= 4:
                    Color(*color); Line(points=points, width=1.15)

            last=float(records[-1]['close'])
            Color(.2, .75, 1, .8)
            Line(points=[left, py(last), right, py(last)], width=.8, dash_length=3, dash_offset=2)

            if self.crosshair and left <= self.crosshair[0] <= right and bottom <= self.crosshair[1] <= top:
                cx, cy = self.crosshair
                Color(.72, .8, .9, .65)
                Line(points=[cx,bottom,cx,top], width=.7)
                Line(points=[left,cy,right,cy], width=.7)
