"""Pruebas visuales básicas. Se omiten si no existe contexto gráfico/Kivy."""
import os,pytest
pytest.importorskip('kivy')
os.environ.setdefault('KIVY_NO_ARGS','1')
from kivy.base import EventLoop
from kivy.graphics import Fbo,ClearColor,ClearBuffers
from ui_theme import MetricCard,NeonButton

def render(widget,w=320,h=120):
    EventLoop.ensure_window(); widget.size=(w,h); widget.pos=(0,0)
    f=Fbo(size=(w,h),with_stencilbuffer=True); f.add(widget.canvas)
    with f: ClearColor(0,0,0,1); ClearBuffers()
    f.draw(); pixels=bytes(f.pixels); return pixels

@pytest.mark.parametrize('widget',[MetricCard('Precio','123','BTC','cyan'),NeonButton(text='ANALIZAR')])
def test_widgets_render_nonempty(widget):
    pixels=render(widget); assert len(pixels)>1000; assert len(set(pixels))>2
