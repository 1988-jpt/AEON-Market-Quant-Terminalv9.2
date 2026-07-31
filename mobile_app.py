"""Interfaz futurista V3, adaptable a escritorio y Android."""
from __future__ import annotations
import asyncio, threading, logging
from concurrent.futures import Future

from kivy.config import Config
Config.set('graphics', 'minimum_width', '360')
Config.set('graphics', 'minimum_height', '640')
from datetime import datetime, timezone
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import Screen, ScreenManager, NoTransition

from platform_runtime import is_android
if is_android():
    from android_analyzer_service import AndroidMarketAnalyzerService as MarketAnalyzerService
else:
    from analyzer_service import MarketAnalyzerService
from async_runtime import AsyncRuntime
if not is_android():
    from backtest_service import BacktestService
    from backtesting_engine import BacktestConfig
    from backtest_report import export_backtest
from interactive_chart import InteractiveMarketChart
from logging_config import setup_logging
from market_scanner import MarketScanner, DEFAULT_SYMBOLS
from profile_manager import ProfileManager, AnalysisProfile
from paper_trading import PaperTradingEngine
from paper_monitor import PaperTradingJournal
from realtime_feed import BinanceRealtimeFeed
from candle_recovery import CandleRecoveryManager
from native_notifications import NativeNotifier
from signal_explainer import explain
from decision_metrics import derive_decision_metrics
from storage import Storage
from system_diagnostics import SystemDiagnostics
from ui_theme import COLORS, MetricCard, NavButton, NeonButton, NeonPanel

logger = logging.getLogger(__name__)


def styled_label(text='', size=13, bold=False, color='text', height=34, markup=False):
    w=Label(text=text,font_size=dp(size),bold=bold,color=COLORS.get(color,COLORS['text']),
            size_hint_y=None,height=dp(height),halign='left',valign='middle',markup=markup)
    w.bind(size=lambda obj,val:setattr(obj,'text_size',val)); return w

def scroll_label(text=''):
    scroll=ScrollView(do_scroll_x=False)
    label=Label(text=text,color=COLORS['text'],size_hint_y=None,markup=True,halign='left',valign='top',padding=(dp(12),dp(12)))
    label.bind(width=lambda obj,val:setattr(obj,'text_size',(max(dp(40),val-dp(24)),None)))
    label.bind(texture_size=lambda obj,val:setattr(obj,'height',val[1]+dp(24)))
    scroll.add_widget(label); scroll.content_label=label; return scroll

class Dashboard(FloatLayout):
    def __init__(self,data_dir:Path,**kwargs):
        super().__init__(**kwargs)
        self.data_dir=data_dir
        self.service=MarketAnalyzerService(str(data_dir/'app_data.db'))
        self.backtest_service=None if is_android() else BacktestService(str(data_dir/'market_cache'))
        self.storage=Storage(str(data_dir/'app_data.db'))
        self.paper=PaperTradingEngine(self.storage)
        self.paper_journal=PaperTradingJournal(str(data_dir/'paper_snapshots.jsonl'))
        self.notifier=NativeNotifier(300)
        self.recovery=CandleRecoveryManager(self.service.client)
        self.scanner=MarketScanner(self.service)
        self.async_runtime=AsyncRuntime()
        self._async_futures:set[Future]=set()
        self.profiles=ProfileManager(str(data_dir/'profiles.json'))
        self.busy=False; self.next_refresh_seconds=0; self.compact_mode=False; self.drawer_open=False; self.last_analysis_monotonic=0.0; self.realtime_feed=None; self.realtime_future=None; self.realtime_generation=0; self.realtime_active=False; self.realtime_requested=False; self.resume_realtime=False; self.last_tick_monotonic=0.0; self.shutting_down=False; self.last_result=None
        with self.canvas.before:
            Color(*COLORS['bg']); self._bg=Rectangle(pos=self.pos,size=self.size)
        self.bind(pos=self._sync_bg,size=self._sync_bg)
        self._build_ui(); self.refresh_history(); Clock.schedule_interval(self._update_clock,1); Clock.schedule_interval(self._update_countdown,1); Clock.schedule_interval(self._paper_snapshot,21600)
    def _sync_bg(self,*_): self._bg.pos=self.pos; self._bg.size=self.size

    def _submit_async(self, coroutine, on_success, on_error):
        """Ejecuta una corutina en el único bucle persistente de la app."""
        try:
            future=self.async_runtime.submit(coroutine)
        except Exception as exc:
            Clock.schedule_once(lambda _dt,msg=str(exc):on_error(msg),0)
            return
        self._async_futures.add(future)
        def completed(done):
            self._async_futures.discard(done)
            if self.shutting_down:
                return
            try:
                result=done.result()
            except Exception as exc:
                logger.exception("Falló una tarea asíncrona de la interfaz")
                message = str(exc).strip() or f"{type(exc).__name__}: error sin detalle"
                Clock.schedule_once(lambda _dt,msg=message:on_error(msg),0)
            else:
                Clock.schedule_once(lambda _dt,value=result:on_success(value),0)
        future.add_done_callback(completed)

    def _build_ui(self):
        # El contenido principal ocupa toda la pantalla. El menú móvil se dibuja
        # por encima, sin comprimir ni deformar el dashboard.
        self.main=BoxLayout(orientation='vertical',padding=dp(10),spacing=dp(8),size_hint=(None,None))
        self.topbar=self._topbar(); self.main.add_widget(self.topbar)
        self.manager=ScreenManager(transition=NoTransition())
        self._build_dashboard_screen(); self._build_market_screen(); self._build_scanner_screen(); self._build_paper_screen()
        if not is_android():
            self._build_backtest_screen()
        self._build_news_screen(); self._build_history_screen(); self._build_diagnostics_screen(); self._build_settings_screen()
        self.main.add_widget(self.manager)
        self.add_widget(self.main)

        # Capa modal: bloquea toques y oscurece el contenido cuando el menú está abierto.
        self.drawer_scrim=Button(text='',background_normal='',background_down='',background_color=(0.0,0.01,0.03,0.78),size_hint=(None,None),opacity=0,disabled=True)
        self.drawer_scrim.bind(on_release=self.toggle_drawer)
        self.add_widget(self.drawer_scrim)

        self.sidebar=NeonPanel(orientation='vertical',size_hint=(None,None),padding=dp(18),spacing=dp(7),radius=0)
        brand=styled_label('[b][color=00D9FF]AEON[/color][/b]  MARKET',21,True,height=60,markup=True)
        subtitle=styled_label('QUANT TERMINAL V9 · MOBILE',9,False,'muted',25)
        self.sidebar.add_widget(brand); self.sidebar.add_widget(subtitle)
        self.nav={}
        pages=[('dashboard','D  Dashboard'),('market','M  Mercado'),('scanner','S  Escáner'),('paper','P  Paper Trading')]
        if not is_android(): pages.append(('backtest','B  Backtesting'))
        pages.extend([('news','N  Noticias'),('history','H  Historial'),('diagnostics','X  Diagnóstico'),('settings','C  Configuración')])
        for key,text in pages:
            b=NavButton(text=text,size_hint_y=None,height=dp(52)); b.bind(on_release=lambda _b,k=key:self.switch_page(k)); b.full_text=text; self.nav[key]=b; self.sidebar.add_widget(b)
        self.sidebar.add_widget(BoxLayout())
        self.connection_status=styled_label('Sistema preparado',11,True,'green',34)
        self.sidebar.add_widget(styled_label('CONECTIVIDAD',9,True,'muted',26)); self.sidebar.add_widget(self.connection_status)
        self.sidebar.add_widget(styled_label('v9.2.0 · mobile production',9,False,'muted',30))
        self.add_widget(self.sidebar)

        self.switch_page('dashboard')
        self.bind(size=self._position_layout,pos=self._position_layout)
        Window.bind(size=self._adapt_layout)
        self._adapt_layout(Window,Window.size)

    def _position_layout(self,*_):
        if self.compact_mode:
            self.main.pos=self.pos; self.main.size=self.size
            self.drawer_scrim.pos=self.pos; self.drawer_scrim.size=self.size
            drawer_width=min(dp(340), self.width*0.88)
            self.sidebar.size=(drawer_width,self.height)
            self.sidebar.pos=(self.x if self.drawer_open else self.x-drawer_width-dp(8),self.y)
        else:
            self.drawer_scrim.opacity=0; self.drawer_scrim.disabled=True
            side=dp(224)
            self.sidebar.pos=self.pos; self.sidebar.size=(side,self.height)
            self.main.pos=(self.x+side,self.y); self.main.size=(max(1,self.width-side),self.height)

    def _topbar(self):
        """Cabecera móvil de dos niveles, sin scroll horizontal ni controles cortados."""
        bar=NeonPanel(orientation='vertical',size_hint_y=None,height=dp(176),padding=dp(10),spacing=dp(7),glow='border')
        header=BoxLayout(size_hint_y=None,height=dp(42),spacing=dp(8))
        self.menu_button=NeonButton(text='MENU',accent='cyan',size_hint_x=None,width=dp(64),font_size=dp(11))
        self.menu_button.bind(on_release=self.toggle_drawer)
        self.mobile_title=styled_label('[b][color=00C7F2]AEON[/color][/b]  MARKET',15,True,'text',40,markup=True)
        self.utc_clock=styled_label('UTC --:--:--',9,True,'muted',40); self.utc_clock.size_hint_x=None; self.utc_clock.width=dp(96)
        header.add_widget(self.menu_button); header.add_widget(self.mobile_title); header.add_widget(Widget()); header.add_widget(self.utc_clock)

        selectors=GridLayout(cols=3,size_hint_y=None,height=dp(50),spacing=dp(7))
        self.symbol_input=TextInput(text='BTC/USDT',multiline=False,font_size=dp(14),foreground_color=COLORS['text'],background_color=COLORS['panel_alt'],padding=(dp(10),dp(13)))
        self.timeframe=Spinner(text='1h',values=('5m','15m','30m','1h','4h','1d'))
        self.limit=Spinner(text='500',values=('300','500','800','1000'))
        for w in (self.symbol_input,self.timeframe,self.limit): selectors.add_widget(w)

        actions=GridLayout(cols=3,size_hint_y=None,height=dp(50),spacing=dp(7))
        self.profile_spinner=Spinner(text='Moderado',values=tuple(self.profiles.load())); self.profile_spinner.bind(text=self.apply_profile)
        self.button=NeonButton(text='ANALIZAR',accent='cyan'); self.button.bind(on_release=self.start_analysis)
        self.live_button=NeonButton(text='EN VIVO',accent='green'); self.live_button.bind(on_release=self.toggle_realtime)
        for w in (self.profile_spinner,self.button,self.live_button): actions.add_widget(w)
        self.top_selectors=selectors; self.top_actions=actions
        bar.add_widget(header); bar.add_widget(selectors); bar.add_widget(actions)
        return bar

    def toggle_drawer(self,*_):
        if not self.compact_mode: return
        self.drawer_open=not self.drawer_open
        self.sidebar.disabled=not self.drawer_open
        self.drawer_scrim.disabled=not self.drawer_open
        self.drawer_scrim.opacity=1 if self.drawer_open else 0
        self.menu_button.text='CERRAR' if self.drawer_open else 'MENU'
        self._position_layout()

    def _screen(self,name):
        s=Screen(name=name); root=BoxLayout(orientation='vertical',spacing=dp(10)); s.add_widget(root); self.manager.add_widget(s); return root
    def _build_dashboard_screen(self):
        screen=Screen(name='dashboard')
        self.dashboard_scroll=ScrollView(do_scroll_x=False, bar_width=dp(4))
        root=BoxLayout(orientation='vertical',spacing=dp(10),size_hint_y=None)
        root.bind(minimum_height=root.setter('height'))
        self.dashboard_root=root
        self.dashboard_scroll.add_widget(root)
        screen.add_widget(self.dashboard_scroll)
        self.manager.add_widget(screen)
        root.add_widget(styled_label('RESUMEN DEL MERCADO',18,True,'text',42))
        self.cards=GridLayout(cols=3,spacing=dp(10),size_hint_y=None,height=dp(220))
        self.signal_card=MetricCard('Señal actual','-','Esperando análisis','cyan')
        self.price_card=MetricCard('Precio','-','USDT','blue')
        self.quality_card=MetricCard('Calidad técnica','-','Índice interno','purple')
        self.sentiment_card=MetricCard('Sentimiento','-','Noticias recientes','green')
        self.risk_card=MetricCard('Riesgo','-','ATR, volatilidad y advertencias','amber')
        self.countdown_card=MetricCard('Actualización','LISTO','Próximo análisis automático','cyan')
        for c in (self.signal_card,self.price_card,self.quality_card,self.sentiment_card,self.risk_card,self.countdown_card):self.cards.add_widget(c)
        root.add_widget(self.cards)
        content=GridLayout(cols=2,spacing=dp(12),size_hint_y=None,height=dp(470)); self.dashboard_content=content
        chart_panel=NeonPanel(orientation='vertical',padding=dp(8),spacing=dp(5)); self.chart_panel=chart_panel
        toolbar=BoxLayout(size_hint_y=None,height=dp(42),spacing=dp(6)); self.live_status=styled_label('MODO NORMAL',10,True,'muted',38)
        reset=NeonButton(text='RESTABLECER',accent='blue',size_hint_x=None,width=dp(130)); reset.bind(on_release=lambda *_:self.market_chart.reset_view())
        toolbar.add_widget(styled_label('MERCADO',14,True,'text',38)); toolbar.add_widget(BoxLayout()); toolbar.add_widget(self.live_status); toolbar.add_widget(reset)
        self.market_chart=InteractiveMarketChart(); chart_panel.add_widget(toolbar); chart_panel.add_widget(self.market_chart)
        right=BoxLayout(orientation='vertical',spacing=dp(10),size_hint_x=.42); self.dashboard_right=right
        signal_panel=NeonPanel(orientation='vertical',padding=dp(12),spacing=dp(3),size_hint_y=.48,glow='cyan')
        signal_panel.add_widget(styled_label('SEÑAL Y CONTEXTO',13,True,'muted',30)); self.signal_hero=styled_label('MANTENER',34,True,'cyan',60); signal_panel.add_widget(self.signal_hero)
        self.signal_context=scroll_label('Ejecuta un análisis para obtener una explicación transparente.'); signal_panel.add_widget(self.signal_context)
        right.add_widget(signal_panel)
        self.quick_stats=scroll_label('[b]ESTADO[/b]\nSin datos todavía.'); quick=NeonPanel(orientation='vertical',padding=dp(6),size_hint_y=.52); quick.add_widget(self.quick_stats); right.add_widget(quick)
        content.add_widget(chart_panel); content.add_widget(right); root.add_widget(content)

    def _build_market_screen(self):
        root=self._screen('market'); root.add_widget(styled_label('ANÁLISIS DETALLADO',19,True,'text',36))
        grid=GridLayout(cols=2,spacing=dp(10)); a=NeonPanel(orientation='vertical',padding=dp(8)); b=NeonPanel(orientation='vertical',padding=dp(8))
        self.summary_label=scroll_label('Pulsa ANALIZAR para comenzar.'); self.indicators_label=scroll_label('Sin indicadores.')
        a.add_widget(styled_label('EXPLICACIÓN DE LA SEÑAL',13,True,'cyan',32)); a.add_widget(self.summary_label)
        b.add_widget(styled_label('INDICADORES Y RIESGO',13,True,'purple',32)); b.add_widget(self.indicators_label)
        grid.add_widget(a); grid.add_widget(b); root.add_widget(grid)

    def _build_scanner_screen(self):
        root=self._screen('scanner'); header=BoxLayout(size_hint_y=None,height=dp(48),spacing=dp(8)); header.add_widget(styled_label('ESCÁNER MULTI-ACTIVO',19,True,'text',46))
        self.scan_symbols=TextInput(text=', '.join(DEFAULT_SYMBOLS),multiline=False,hint_text='BTC/USDT, ETH/USDT')
        scan=NeonButton(text='ESCANEAR MERCADO',accent='cyan',size_hint_x=None,width=dp(180)); scan.bind(on_release=self.start_scan)
        header.add_widget(self.scan_symbols); header.add_widget(scan); root.add_widget(header)
        panel=NeonPanel(orientation='vertical',padding=dp(8)); self.scanner_label=scroll_label('Clasifica oportunidades por señal, calidad, régimen y volumen.'); panel.add_widget(self.scanner_label); root.add_widget(panel)

    def _build_paper_screen(self):
        root=self._screen('paper'); root.add_widget(styled_label('SIMULADOR PAPER TRADING',19,True,'text',36))
        actions=BoxLayout(size_hint_y=None,height=dp(48),spacing=dp(8))
        open_btn=NeonButton(text='ABRIR DESDE SEÑAL ACTUAL',accent='green')
        close_btn=NeonButton(text='CERRAR POSICIÓN',accent='red')
        refresh_btn=NeonButton(text='ACTUALIZAR',accent='cyan')
        open_btn.bind(on_release=self.open_paper_position); close_btn.bind(on_release=self.close_paper_position); refresh_btn.bind(on_release=lambda *_:self.refresh_paper())
        actions.add_widget(open_btn); actions.add_widget(close_btn); actions.add_widget(refresh_btn); root.add_widget(actions)
        panel=NeonPanel(orientation='vertical',padding=dp(8)); self.paper_label=scroll_label('Simulación local. Nunca envía órdenes reales a Binance.'); panel.add_widget(self.paper_label); root.add_widget(panel)
        self.refresh_paper()

    def _build_backtest_screen(self):
        root=self._screen('backtest'); root.add_widget(styled_label('LABORATORIO DE ESTRATEGIAS',19,True,'text',36))
        controls=GridLayout(cols=4,spacing=dp(6),size_hint_y=None,height=dp(92))
        self.bt_capital=TextInput(text='10000',multiline=False,hint_text='Capital'); self.bt_risk=TextInput(text='1.0',multiline=False,hint_text='Riesgo %')
        self.bt_cost=TextInput(text='0.10',multiline=False,hint_text='Comisión %'); self.bt_slippage=TextInput(text='0.03',multiline=False,hint_text='Slippage %')
        self.bt_bars=TextInput(text='5000',multiline=False,hint_text='Velas'); self.bt_start=TextInput(text='',multiline=False,hint_text='Inicio YYYY-MM-DD')
        self.bt_end=TextInput(text='',multiline=False,hint_text='Fin YYYY-MM-DD'); self.bt_market=Spinner(text='spot',values=('spot','futures'))
        for x in (self.bt_capital,self.bt_risk,self.bt_cost,self.bt_slippage,self.bt_bars,self.bt_start,self.bt_end,self.bt_market):controls.add_widget(x)
        root.add_widget(controls)
        actions=BoxLayout(size_hint_y=None,height=dp(48),spacing=dp(8)); self.bt_button=NeonButton(text='EJECUTAR BACKTEST',accent='blue'); self.bt_opt_button=NeonButton(text='WALK-FORWARD',accent='purple')
        self.bt_button.bind(on_release=lambda *_:self.start_backtest(False)); self.bt_opt_button.bind(on_release=lambda *_:self.start_backtest(True)); actions.add_widget(self.bt_button); actions.add_widget(self.bt_opt_button); root.add_widget(actions)
        panel=NeonPanel(orientation='vertical',padding=dp(8)); self.backtest_label=scroll_label('Simulación causal con costes, gaps, mark-to-market y confirmación multi-temporal.'); panel.add_widget(self.backtest_label); root.add_widget(panel)

    def _build_news_screen(self):
        root=self._screen('news'); root.add_widget(styled_label('NOTICIAS Y SENTIMIENTO',19,True,'text',36)); p=NeonPanel(orientation='vertical',padding=dp(8)); self.news_label=scroll_label('Sin noticias.'); p.add_widget(self.news_label); root.add_widget(p)
    def _build_history_screen(self):
        root=self._screen('history'); root.add_widget(styled_label('HISTORIAL DE SEÑALES',19,True,'text',36)); p=NeonPanel(orientation='vertical',padding=dp(8)); self.history_label=scroll_label('Sin historial.'); p.add_widget(self.history_label); root.add_widget(p)
    def _build_diagnostics_screen(self):
        root=self._screen('diagnostics'); h=BoxLayout(size_hint_y=None,height=dp(48)); h.add_widget(styled_label('SALUD DEL SISTEMA',19,True,'text',46)); b=NeonButton(text='EJECUTAR DIAGNÓSTICO',accent='green',size_hint_x=None,width=dp(210)); b.bind(on_release=self.start_diagnostics); h.add_widget(b); root.add_widget(h)
        p=NeonPanel(orientation='vertical',padding=dp(8)); self.diagnostic_label=scroll_label('Comprueba Binance, latencia, base de datos y almacenamiento.'); p.add_widget(self.diagnostic_label); root.add_widget(p)
    def _build_settings_screen(self):
        root=self._screen('settings'); root.add_widget(styled_label('PERFILES Y CONFIGURACIÓN',19,True,'text',36))
        p=NeonPanel(orientation='vertical',padding=dp(12),spacing=dp(8),size_hint_y=None,height=dp(250)); self.profile_name=TextInput(text='Personalizado',multiline=False,hint_text='Nombre del perfil')
        self.profile_confidence=TextInput(text='70',multiline=False,hint_text='Calidad mínima'); save=NeonButton(text='GUARDAR PERFIL',accent='cyan',size_hint_y=None,height=dp(44)); save.bind(on_release=self.save_profile)
        p.add_widget(styled_label('Guarda temporalidad, cantidad de velas, riesgo y tipo de mercado.',12,False,'muted',34)); p.add_widget(self.profile_name); p.add_widget(self.profile_confidence); p.add_widget(save); root.add_widget(p); root.add_widget(BoxLayout())

    def switch_page(self,name):
        self.manager.current=name
        for key,b in self.nav.items(): b.set_active(key==name)
        if self.compact_mode and self.drawer_open:
            self.toggle_drawer()

    def _adapt_layout(self,_window,size):
        width,height=size
        compact=width < dp(900)
        phone=width < dp(620)
        very_small=width < dp(380) or height < dp(700)
        self.compact_mode=compact
        if compact:
            if not self.drawer_open:
                self.sidebar.disabled=True; self.drawer_scrim.disabled=True; self.drawer_scrim.opacity=0
            self.menu_button.opacity=1; self.menu_button.disabled=False; self.menu_button.width=dp(58 if very_small else 64)
            self.mobile_title.text='[b][color=00C7F2]AEON[/color][/b]  MARKET'
            self.main.padding=dp(6 if very_small else 8); self.main.spacing=dp(6)
            self.topbar.height=dp(166 if very_small else 176)
            self.cards.cols=2
            card_h=max(dp(148), min(dp(178), (height-dp(245))/3))
            self.cards.height=card_h*3+dp(20)
            self.dashboard_content.cols=1; self.dashboard_content.rows=2
            chart_h=max(dp(350), min(dp(450), height*0.57))
            self.chart_panel.size_hint_y=None; self.chart_panel.height=chart_h
            self.dashboard_right.size_hint_x=1; self.dashboard_right.size_hint_y=None; self.dashboard_right.height=dp(300 if very_small else 330)
            self.dashboard_content.height=chart_h+self.dashboard_right.height+dp(12)
            self.signal_hero.font_size=dp(25 if very_small else 29)
            self.utc_clock.width=dp(88 if very_small else 96)
        else:
            self.drawer_open=False; self.sidebar.disabled=False; self.sidebar.opacity=1
            self.drawer_scrim.opacity=0; self.drawer_scrim.disabled=True
            self.menu_button.opacity=0; self.menu_button.disabled=True; self.menu_button.width=0
            self.mobile_title.text='[b][color=00C7F2]AEON[/color][/b]  MARKET QUANT TERMINAL'
            self.main.padding=dp(14); self.main.spacing=dp(10)
            self.topbar.height=dp(176)
            self.cards.cols=3; self.cards.height=dp(230)
            self.dashboard_content.cols=2; self.dashboard_content.height=dp(470)
            self.chart_panel.size_hint_y=1
            self.dashboard_right.size_hint_x=.40; self.dashboard_right.size_hint_y=1
            self.signal_hero.font_size=dp(34)
        for widget in (self.symbol_input,self.timeframe,self.limit,self.profile_spinner,self.button,self.live_button):
            widget.font_size=dp(11 if very_small else (12 if phone else 14))
        self._position_layout()
    def _update_clock(self,_dt): self.utc_clock.text=datetime.now(timezone.utc).strftime('UTC %H:%M:%S')

    def _update_countdown(self, _dt):
        if self.next_refresh_seconds > 0:
            self.next_refresh_seconds -= 1
        if hasattr(self, 'countdown_card'):
            value = f'{self.next_refresh_seconds:02d}s' if self.next_refresh_seconds > 0 else 'LISTO'
            self.countdown_card.set(value, 'Próximo análisis automático', 'cyan')

    def apply_profile(self,_spinner,name):
        p=self.profiles.load().get(name)
        if not p:return
        self.timeframe.text=p.timeframe
        self.limit.text=str(min(p.bars,1000))
        if hasattr(self,'bt_risk'): self.bt_risk.text=str(p.risk_pct)
        if hasattr(self,'bt_market'): self.bt_market.text=p.market_type
        self.profile_confidence.text=str(p.min_confidence)
    def save_profile(self,*_):
        try:
            risk=float(self.bt_risk.text) if hasattr(self,'bt_risk') else 1.0
            market=self.bt_market.text if hasattr(self,'bt_market') else 'spot'
            p=AnalysisProfile(self.profile_name.text.strip() or 'Personalizado',self.timeframe.text,int(self.limit.text),float(self.profile_confidence.text),risk,market)
        except ValueError:return
        self.profiles.save(p); self.profile_spinner.values=tuple(self.profiles.load()); self.profile_spinner.text=p.name

    def start_analysis(self,*_):
        if self.busy:return
        symbol=self.symbol_input.text.strip().upper().replace('-','/')
        if '/' not in symbol:self.summary_label.content_label.text='Formato inválido. Usa BTC/USDT.';return
        self.busy=True; self.button.disabled=True; self.button.text='PROCESANDO...'; self.connection_status.text='Analizando mercado'; self.switch_page('dashboard')
        self._submit_async(self.service.analyze(symbol,self.timeframe.text,int(self.limit.text)),self.show_result,self.show_error)
    def show_result(self,result):
        d=result.decision; tr={'BUY':'COMPRAR','SELL':'VENDER','HOLD':'MANTENER'}; accent={'BUY':'green','SELL':'red','HOLD':'amber'}.get(d['signal'],'cyan')
        metrics=derive_decision_metrics(d,result.price)
        self.next_refresh_seconds=60 if self.realtime_active else 0
        self.signal_card.set(tr.get(d['signal'],d['signal']),d.get('market_regime',{}).get('regime','-'),accent); self.price_card.set(f"{result.price:,.4f}",result.symbol,'blue'); self.quality_card.set(f"{d['confidence']:.1f}/100",f"Score {d['score']:+.2f}",'purple'); self.sentiment_card.set(result.sentiment['label'],f"Score {result.sentiment['score']:+.2f}",'green'); self.risk_card.set(metrics['risk_level'],f"Riesgo {metrics['risk_score']:.1f}/100 · ATR {metrics['atr_pct']:.2f}%",'amber')
        self.signal_hero.text=tr.get(d['signal'],d['signal']); self.signal_hero.color=COLORS[accent]
        ex=explain(d); positives='\n'.join('+ '+x for x in ex['positives']) or '-'; risks='\n'.join('! '+x for x in ex['risks']) or 'Sin advertencias relevantes.'
        self.signal_context.content_label.text=f"[b]Calidad técnica:[/b] {d['confidence']:.1f}/100\n[b]Régimen:[/b] {d.get('market_regime',{}).get('regime','-')}\n[b]Temporalidad superior:[/b] {d.get('higher_timeframe',{}).get('bias','-')}\n\n[b]FORTALEZAS[/b]\n{positives}\n\n[b]RIESGOS[/b]\n{risks}"
        supports=', '.join(f'{x:,.4f}' for x in d.get('supports',[])) or 'No detectados'; resist=', '.join(f'{x:,.4f}' for x in d.get('resistances',[])) or 'No detectadas'; plan=d.get('trade_plan') or {}
        self.summary_label.content_label.text=f"[b]RESUMEN[/b]\n{ex['summary']}\n\n[b]Confirmaciones positivas[/b]\n{positives}\n\n[b]Advertencias[/b]\n{risks}\n\n[b]Soportes:[/b] {supports}\n[b]Resistencias:[/b] {resist}"
        self.indicators_label.content_label.text=(f"[b]RSI:[/b] {d['rsi']:.2f}\n[b]MACD:[/b] {d['macd']:.6f}\n[b]ADX:[/b] {d['adx']:.2f}\n[b]ATR:[/b] {d['atr']:.6f}\n[b]VWAP:[/b] {d['vwap']:.4f}\n[b]Volumen relativo:[/b] {d.get('volume_ratio',0):.2f}x\n[b]Eficiencia:[/b] {d.get('efficiency_ratio',0):.2f}\n\n[b]PLAN ORIENTATIVO[/b]\nEntrada: {plan.get('entry','-')}\nStop: {plan.get('stop_loss','-')}\nTP1: {plan.get('take_profit_1','-')}\nTP2: {plan.get('take_profit_2','-')}")
        self.quick_stats.content_label.text=f"[b]PUNTUACIONES[/b]\nCompradores: {d.get('long_score',0):.2f}\nVendedores: {d.get('short_score',0):.2f}\nDiferencia: {d.get('score',0):+.2f}\n\n[b]PATRONES[/b]\n{', '.join(d.get('patterns',[])) or 'Ninguno relevante'}"
        self.news_label.content_label.text='\n\n'.join(f"[b]{n.title}[/b]\nSentimiento {n.score:+.2f} · {n.published}" for n in result.news) or 'No se pudieron obtener noticias.'
        self.last_result=result
        if d.get('signal') in ('BUY','SELL') and float(d.get('confidence',0))>=75:
            self.notifier.send(f"Señal {result.symbol}",f"{d['signal']} · calidad {d['confidence']:.1f}/100 · precio {result.price:.4f}",key=f"{result.symbol}:{d['signal']}")
        try:
            self.paper.mark(result.symbol,result.price)
            self.refresh_paper()
        except Exception:
            logger.exception('No se pudo actualizar paper trading')
        self.market_chart.set_data(result.dataframe,result.decision,result.symbol); self.connection_status.text='Datos actualizados'; self._finish(); self.refresh_history()

    def start_scan(self,*_):
        if self.busy:return
        symbols=[s.strip().upper().replace('-','/') for s in self.scan_symbols.text.split(',') if '/' in s][:20]
        if not symbols:self.scanner_label.content_label.text='Introduce pares separados por comas.';return
        self.busy=True; self.scanner_label.content_label.text='Escaneando activos en paralelo...'
        self._submit_async(self.scanner.scan(symbols,self.timeframe.text,int(self.limit.text)),self.show_scan,self.show_scan_error)
    def show_scan(self,rows):
        lines=['[b]PAR             SEÑAL     CALIDAD   SCORE     RÉGIMEN              VOLUMEN[/b]']
        for r in rows:lines.append(f"{r.symbol:<14} {r.signal:<8} {r.confidence:>6.1f}   {r.score:>+7.2f}   {r.regime:<20} {r.volume_ratio:>5.2f}x")
        self.scanner_label.content_label.text='\n'.join(lines); self.busy=False
    def show_scan_error(self,msg):self.scanner_label.content_label.text='[b]Error:[/b] '+msg;self.busy=False

    def toggle_realtime(self,*_):
        if self.realtime_active or self.realtime_requested:
            self.stop_realtime()
            return
        symbol=self.symbol_input.text.strip().upper().replace('-','/')
        if '/' not in symbol:
            self._set_live_status('Símbolo inválido')
            return
        self.realtime_generation+=1
        generation=self.realtime_generation
        self.realtime_requested=True; self.realtime_active=True
        self.live_button.text='DETENER'; self.live_button.background_color=COLORS['red']
        self._set_live_status('Conectando…')

        async def on_tick(tick):
            if generation==self.realtime_generation and not self.shutting_down:
                Clock.schedule_once(lambda _dt,item=tick:self._apply_tick(item),0)
        async def on_status(text):
            if generation==self.realtime_generation and not self.shutting_down:
                Clock.schedule_once(lambda _dt,value=text:self._set_live_status(value),0)
        async def on_gap(last_ms,current_ms):
            rows=await self.recovery.recover(symbol,self.timeframe.text,last_ms,current_ms)
            from realtime_feed import RealtimeTick
            for row in rows:
                await on_tick(RealtimeTick(symbol,self.timeframe.text,int(row[0]),float(row[1]),float(row[2]),float(row[3]),float(row[4]),float(row[5]),True))

        feed=BinanceRealtimeFeed(symbol,self.timeframe.text,on_tick,on_status,on_gap=on_gap)
        self.realtime_feed=feed
        future=self.async_runtime.submit(feed.run())
        self.realtime_future=future
        def completed(done):
            if self.realtime_future is done:self.realtime_future=None
            if self.realtime_feed is feed:self.realtime_feed=None
            self.realtime_active=False; self.realtime_requested=False
            if self.shutting_down:return
            try:done.result()
            except Exception as exc:
                logger.exception('Falló el tiempo real')
                Clock.schedule_once(lambda _dt,msg=str(exc):self._set_live_status('Error de conexión'),0)
            Clock.schedule_once(lambda _dt:self._reset_live_button(),0)
        future.add_done_callback(completed)

    def stop_realtime(self,wait=False,update_ui=True):
        self.realtime_generation+=1
        self.realtime_requested=False
        feed,future=self.realtime_feed,self.realtime_future
        if update_ui and not self.shutting_down:self._set_live_status('Desconectando…')
        if feed is not None:
            try:
                stopper=self.async_runtime.submit(feed.stop())
                if wait:stopper.result(timeout=4)
            except Exception: logger.debug('Cierre de feed incompleto',exc_info=True)
        if future is not None and wait:
            try:future.result(timeout=5)
            except Exception:pass
        self.realtime_feed=None; self.realtime_future=None; self.realtime_active=False
        if update_ui and not self.shutting_down:self._reset_live_button()

    def _reset_live_button(self):
        self.live_button.text='EN VIVO'; self.live_button.background_color=COLORS['green']
        if not self.realtime_active:self._set_live_status('MODO NORMAL')

    def _set_live_status(self,text):
        self.live_status.text=text.upper(); self.connection_status.text=text

    def _apply_tick(self,tick):
        import time
        self.last_tick_monotonic=time.monotonic()
        self.market_chart.update_last_candle(tick.timestamp_ms,{'open':tick.open,'high':tick.high,'low':tick.low,'close':tick.close,'volume':tick.volume})
        stamp=datetime.now().strftime('%H:%M:%S')
        self.price_card.set(f'{tick.close:,.4f}',f'En vivo · {stamp}','green')
        if tick.closed and not self.busy:self.start_analysis()


    def _paper_snapshot(self,_dt=0):
        try:
            account=self.paper.account(); opened=sum(1 for p in self.storage.get_paper_positions(500) if p.get('status')=='OPEN'); self.paper_journal.append(account,opened)
        except Exception: logger.exception('No se pudo guardar snapshot paper')

    def refresh_paper(self):
        account=self.paper.account(); positions=self.storage.get_paper_positions(30)
        lines=[f"[b]Balance paper:[/b] {account['balance']:,.2f} USDT",f"[b]PnL realizado:[/b] {account['realized_pnl']:+,.2f} USDT",'', '[b]OPERACIONES[/b]']
        for p in positions:
            status=p['status']; end=f" → {p['exit']:,.4f} · PnL {p['net_pnl']:+,.2f}" if status=='CLOSED' else f" · Stop {p['stop']:,.4f} · TP {p['target']:,.4f}"
            lines.append(f"{p['symbol']} · {p['side']} · {status} · {p['entry']:,.4f}{end}")
        self.paper_label.content_label.text='\n'.join(lines) if positions else '\n'.join(lines+['Sin operaciones todavía.'])

    def open_paper_position(self,*_):
        if not self.last_result:
            self.paper_label.content_label.text='Ejecuta primero un análisis.'; return
        try:
            position_id=self.paper.open_from_decision(self.last_result.symbol,self.last_result.price,self.last_result.decision)
            if position_id is None: raise ValueError('La señal actual es HOLD; no se abrió una operación.')
            self.refresh_paper(); self.switch_page('paper')
        except Exception as exc:
            logger.exception('No se pudo abrir posición paper'); self.paper_label.content_label.text='[b]Error:[/b] '+str(exc)

    def close_paper_position(self,*_):
        symbol=self.symbol_input.text.strip().upper().replace('-','/')
        price=self.last_result.price if self.last_result and self.last_result.symbol==symbol else None
        if price is None:
            self.paper_label.content_label.text='Analiza el símbolo para obtener un precio de cierre actual.'; return
        try:
            self.paper.close(symbol,price,'manual'); self.refresh_paper()
        except Exception as exc:
            self.paper_label.content_label.text='[b]Error:[/b] '+str(exc)

    def start_backtest(self,optimize=False):
        if is_android():
            self.show_backtest_error('El backtesting avanzado usa Pandas y está reservado al escritorio. Android utiliza el motor NumPy ligero para análisis en vivo.')
            return
        if self.busy:return
        symbol=self.symbol_input.text.strip().upper().replace('-','/')
        try:p=dict(capital=float(self.bt_capital.text),risk=float(self.bt_risk.text)/100,fee=float(self.bt_cost.text)/100,slippage=float(self.bt_slippage.text)/100,bars=int(self.bt_bars.text),since=self.bt_start.text.strip() or None,until=self.bt_end.text.strip() or None,market=self.bt_market.text)
        except ValueError:self.show_backtest_error('Revisa los parámetros numéricos.');return
        self.busy=True;self.bt_button.disabled=True;self.bt_opt_button.disabled=True;self.backtest_label.content_label.text='Procesando simulación histórica…'
        cfg=BacktestConfig(initial_capital=p['capital'],risk_per_trade=p['risk'],fee_rate=p['fee'],slippage_rate=p['slippage'],market_type=p['market'],allow_short=p['market']=='futures',timeframe=self.timeframe.text)
        self._submit_async(self.backtest_service.run(symbol,self.timeframe.text,p['bars'],optimize,cfg,p['since'],p['until'],True),self.show_backtest,self.show_backtest_error)
    def show_backtest(self,sr):
        r=sr.result;m=r.metrics;paths=export_backtest(r,str(self.data_dir/'backtests'),f"{sr.symbol.replace('/','_')}_{sr.timeframe}")
        extra=''
        if sr.optimization:o=sr.optimization;extra=f"\n[b]Robustez walk-forward:[/b] {o['robustness']}\n[b]Ventanas:[/b] {o['windows_count']} · positivas {o['positive_windows_pct']:.1f}%\n[b]Retorno mediano OOS:[/b] {o['median_test_return_pct']:.2f}%"
        try:self.storage.save_backtest(sr.symbol,sr.timeframe,sr.period_start,sr.period_end,r,str(self.data_dir/'backtests'))
        except Exception:pass
        mc=m.get('monte_carlo',{}); cal=m.get('confidence_calibration',{})
        mc_text=(f"\n\n[b]MONTE CARLO[/b]\nCapital mediano: {mc.get('final_capital_median','-')}\nDrawdown P95: {mc.get('max_drawdown_p95','-')}%\nRiesgo de ruina: {mc.get('risk_of_ruin_pct','-')}%" if mc.get('available') else '\n\nMonte Carlo: requiere al menos 2 operaciones.')
        cal_text=f"\nCalibración de calidad: {'disponible' if cal.get('calibrated') else 'muestras insuficientes'}"
        self.backtest_label.content_label.text=f"[b]{sr.symbol} · {sr.timeframe}[/b]\nPeriodo: {sr.period_start} → {sr.period_end}\nVelas: {sr.rows}\n\nCapital inicial: {m['initial_capital']:,.2f} USDT\nCapital final: {m['final_capital']:,.2f} USDT\nRetorno: {m['net_return_pct']:.2f}%\nOperaciones: {m['total_trades']}\nAcierto: {m['win_rate_pct']:.2f}%\nProfit Factor: {m['profit_factor']}\nDrawdown: {m['max_drawdown_pct']:.2f}%\nSharpe: {m['sharpe']}\nSortino: {m['sortino']}\nRacha máxima de pérdidas: {m.get('max_consecutive_losses',0)}\nSalidas parciales: {m.get('partial_exit_trades',0)}{cal_text}{mc_text}{extra}\n\nReportes:\n{paths['metrics']}\n{paths['trades']}\n{paths['equity']}\n{paths['chart']}"
        self.busy=False;self.bt_button.disabled=False;self.bt_opt_button.disabled=False
    def show_backtest_error(self,msg):self.backtest_label.content_label.text='[b]Error:[/b] '+msg;self.busy=False;self.bt_button.disabled=False;self.bt_opt_button.disabled=False

    def start_diagnostics(self,*_):
        self.diagnostic_label.content_label.text='Ejecutando comprobaciones...'; threading.Thread(target=self._diagnostic_worker,daemon=True).start()
    def _diagnostic_worker(self):
        r=SystemDiagnostics(str(self.data_dir),str(self.data_dir/'app_data.db')).run();Clock.schedule_once(lambda _dt:self.show_diagnostics(r),0)
    def show_diagnostics(self,r):
        lines=[f"[b]Python:[/b] {r['python']}",f"[b]Plataforma:[/b] {r['platform']}",'']
        for name,v in r['checks'].items():lines.append(f"[b]{name.upper()}:[/b] {'OK' if v.get('ok') else 'ERROR'}"+(f" · {v.get('latency_ms')} ms" if v.get('latency_ms') is not None else '')+(f" · {v.get('error')}" if v.get('error') else ''))
        self.diagnostic_label.content_label.text='\n'.join(lines)
    def show_error(self, msg):
        safe = str(msg).strip() or 'Error desconocido.'
        text = '[b]NO SE PUDO COMPLETAR EL ANÁLISIS[/b]\n' + safe
        self.summary_label.content_label.text = '[b]Error:[/b] ' + safe
        self.signal_context.content_label.text = text + '\n\nRevisa Diagnóstico y el archivo app.log.'
        self.quick_stats.content_label.text = '[b]ESTADO[/b]\nError de análisis\n\n' + safe
        self.signal_hero.text = 'ERROR'
        self.signal_hero.color = COLORS['red']
        self.connection_status.text = '- Error de análisis'
        logger.error('Error mostrado al usuario: %s', safe)
        self._finish()
    def _finish(self):self.busy=False;self.button.disabled=False;self.button.text='ANALIZAR'
    def refresh_history(self):
        lines=[]
        for row in self.service.storage.get_recent_signals(30):
            date=datetime.fromtimestamp(row['ts']/1000).strftime('%d/%m/%Y %H:%M');lines.append(f"[b]{date} · {row['symbol']} · {row['signal']}[/b]\n{row['price']:,.4f}\n{row.get('details') or ''}")
        self.history_label.content_label.text='\n\n'.join(lines) or 'Aún no hay análisis guardados.'

class StartupShell(BoxLayout):
    """Pantalla mínima que aparece antes de cargar los servicios pesados."""
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(24), spacing=dp(16), **kwargs)
        with self.canvas.before:
            Color(*COLORS["bg"])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_bg, size=self._sync_bg)
        self.add_widget(Widget())
        self.title_label = styled_label(
            "[b][color=00D9FF]AEON[/color][/b] MARKET QUANT TERMINAL",
            22, True, height=70, markup=True,
        )
        self.title_label.halign = "center"
        self.add_widget(self.title_label)
        self.status_label = styled_label(
            "Preparando entorno seguro...", 13, False, "muted", 80
        )
        self.status_label.halign = "center"
        self.add_widget(self.status_label)
        self.retry_button = Button(
            text="REINTENTAR INICIO",
            size_hint_y=None,
            height=dp(48),
            opacity=0,
            disabled=True,
        )
        self.add_widget(self.retry_button)
        self.add_widget(Widget())

    def _sync_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def set_error(self, message: str):
        self.status_label.text = (
            "[b]No se pudo iniciar AEON.[/b]\n"
            + message
            + "\n\nSe guardó aeon_startup_crash.log en los datos de la aplicación."
        )
        self.status_label.markup = True
        self.retry_button.opacity = 1
        self.retry_button.disabled = False


class MarketAnalyzerApp(App):
    title = "AEON Market Quant Terminal"

    def build(self):
        Window.clearcolor = COLORS["bg"]
        self.dashboard = None
        self.data_dir = Path(self.user_data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        setup_logging(str(self.data_dir / "app.log"), force=True)
        from android_runtime_guard import install_exception_hook
        install_exception_hook(self.data_dir)

        self.shell = StartupShell()
        self.shell.retry_button.bind(on_release=lambda *_: self._schedule_startup())
        return self.shell

    def on_start(self):
        self._schedule_startup()
        if is_android():
            Clock.schedule_once(self._request_android_permissions, 0.5)

    def _schedule_startup(self):
        self.shell.retry_button.disabled = True
        self.shell.retry_button.opacity = 0
        self.shell.status_label.text = "Cargando componentes del mercado..."
        Clock.schedule_once(self._initialize_dashboard, 0.15)

    def _initialize_dashboard(self, _dt):
        try:
            dashboard = Dashboard(self.data_dir)
            self.dashboard = dashboard
            self.root.clear_widgets()
            self.root.add_widget(dashboard)
            logger.info("Interfaz Android iniciada correctamente")
        except Exception as exc:
            logger.exception("Fallo durante el arranque de la interfaz")
            try:
                from android_runtime_guard import write_crash_report
                write_crash_report(exc, self.data_dir)
            except Exception:
                pass
            safe = str(exc).strip() or type(exc).__name__
            self.shell.set_error(safe)

    def _request_android_permissions(self, _dt):
        # INTERNET es un permiso normal y no debe solicitarse en tiempo de ejecución.
        try:
            from android.permissions import Permission, request_permissions
            permission = getattr(Permission, "POST_NOTIFICATIONS", None)
            if permission:
                request_permissions([permission])
        except Exception:
            logger.warning("No se pudo solicitar POST_NOTIFICATIONS", exc_info=True)

    def on_pause(self):
        if self.dashboard is not None:
            self.dashboard.resume_realtime = bool(self.dashboard.realtime_active or self.dashboard.realtime_requested)
            self.dashboard.stop_realtime(wait=True, update_ui=False)
        return True

    def on_resume(self):
        if self.dashboard is not None and self.dashboard.resume_realtime:
            self.dashboard.resume_realtime=False
            Clock.schedule_once(lambda _dt:self.dashboard.toggle_realtime(),0.8)
        return None

    def on_stop(self):
        dashboard = self.dashboard
        if dashboard is None:
            return
        dashboard.shutting_down = True
        dashboard.stop_realtime(wait=True, update_ui=False)
        for future in list(dashboard._async_futures):
            future.cancel()
        try:
            close_result = dashboard.service.close()
            if asyncio.iscoroutine(close_result):
                dashboard.async_runtime.submit(close_result).result(timeout=8)
        except Exception:
            logger.exception("No se pudo cerrar correctamente el servicio de análisis")
        try:
            dashboard.async_runtime.shutdown()
        except Exception:
            logger.exception("No se pudo cerrar AsyncRuntime")

