"""Motor de backtesting causal con ejecución y gestión de riesgo avanzadas."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
import math
import numpy as np
import pandas as pd

from advanced_strategy import AdvancedStrategy
from confidence_calibration import calibrate_confidence
from monte_carlo import run_monte_carlo
from technical_indicators import add_quality_indicators

ANNUAL_BARS = {'1m':525600,'3m':175200,'5m':105120,'15m':35040,'30m':17520,
               '1h':8760,'2h':4380,'4h':2190,'6h':1460,'8h':1095,'12h':730,
               '1d':365,'3d':121.67,'1w':52}


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float = 10_000.0
    risk_per_trade: float = .01
    fee_rate: float = .001
    slippage_rate: float = .0003
    spread_rate: float = .0001
    min_confidence: float = 68.
    min_abs_score: float = 2.
    warmup_bars: int = 220
    max_bars_in_trade: int = 80
    allow_long: bool = True
    allow_short: bool = True
    conservative_intrabar: bool = True
    timeframe: str = '1h'
    max_notional_fraction: float = 1.
    min_trade_notional: float = 10.
    market_type: str = 'spot'
    partial_take_profit: bool = True
    partial_fraction: float = .5
    partial_rr: float = 1.5
    final_rr: float = 2.5
    break_even_after_partial: bool = True
    trailing_stop: bool = True
    trailing_atr_multiple: float = 2.0
    max_daily_loss_pct: float = 3.0
    max_consecutive_losses: int = 4
    monte_carlo_simulations: int = 1000


@dataclass
class Trade:
    side: str
    signal_time: str
    entry_time: str
    exit_time: str
    entry: float
    exit: float
    stop: float
    target: float
    quantity: float
    gross_pnl: float
    fees: float
    net_pnl: float
    return_pct: float
    bars_held: int
    exit_reason: str
    confidence: float
    score: float
    regime: str
    partial_pnl: float = 0.0


@dataclass
class BacktestResult:
    config: Dict[str, Any]
    metrics: Dict[str, Any]
    trades: List[Dict[str, Any]]
    equity_curve: pd.DataFrame


class BacktestEngine:
    def __init__(self, strategy: Optional[AdvancedStrategy] = None):
        self.strategy = strategy or AdvancedStrategy()

    def run(self, data: pd.DataFrame, config: Optional[BacktestConfig] = None,
            higher_timeframe_data: Optional[pd.DataFrame] = None) -> BacktestResult:
        cfg = self._validated_config(config or BacktestConfig())
        df = add_quality_indicators(self._validate(data))
        higher = None
        if higher_timeframe_data is not None and len(higher_timeframe_data):
            higher = add_quality_indicators(self._validate(higher_timeframe_data))
        if len(df) <= cfg.warmup_bars + 2:
            raise ValueError(f'Se requieren más de {cfg.warmup_bars + 2} velas.')

        capital = float(cfg.initial_capital)
        peak = capital
        rows: list[dict[str, Any]] = []
        trades: list[Trade] = []
        position = None
        consecutive_losses = 0
        daily_start_equity: dict[str, float] = {}

        for i in range(cfg.warmup_bars, len(df) - 1):
            now = df.index[i]
            bar = df.iloc[i]
            day_key = str(pd.Timestamp(now).date())
            daily_start_equity.setdefault(day_key, capital)

            if position is not None:
                closed = self._check_exit(position, bar, now, i, cfg)
                if closed is not None:
                    capital += closed.net_pnl
                    trades.append(closed)
                    consecutive_losses = consecutive_losses + 1 if closed.net_pnl < 0 else 0
                    position = None

            day_loss_pct = ((capital / daily_start_equity[day_key]) - 1) * 100
            risk_locked = day_loss_pct <= -abs(cfg.max_daily_loss_pct)
            loss_streak_locked = consecutive_losses >= cfg.max_consecutive_losses

            if position is None and not risk_locked and not loss_streak_locked:
                higher_slice = None
                if higher is not None:
                    higher_slice = higher.loc[higher.index <= now]
                    if len(higher_slice) < 30:
                        higher_slice = None
                decision = self.strategy.decide(df.iloc[:i + 1], 0.0, higher_slice)
                signal = decision.get('signal')
                valid = (
                    signal in ('BUY', 'SELL')
                    and float(decision.get('confidence', 0)) >= cfg.min_confidence
                    and abs(float(decision.get('score', 0))) >= cfg.min_abs_score
                    and ((signal == 'BUY' and cfg.allow_long)
                         or (signal == 'SELL' and cfg.allow_short))
                )
                if valid:
                    position = self._open_position(signal, df.iloc[i + 1], df.index[i + 1],
                                                   now, decision, capital, cfg, i + 1)

            mark = capital + self._unrealized(position, float(bar['close'])) if position else capital
            peak = max(peak, mark)
            rows.append({'timestamp': now, 'cash_equity': capital, 'equity': mark,
                         'unrealized_pnl': mark - capital,
                         'drawdown_pct': (mark / peak - 1) * 100,
                         'risk_lock': risk_locked or loss_streak_locked})

        if position is not None:
            last = df.iloc[-1]
            closed = self._force_close(position, float(last['close']), df.index[-1],
                                       len(df) - 1, cfg, 'fin_de_datos')
            capital += closed.net_pnl
            trades.append(closed)

        peak = max(peak, capital)
        rows.append({'timestamp': df.index[-1], 'cash_equity': capital, 'equity': capital,
                     'unrealized_pnl': 0., 'drawdown_pct': (capital / peak - 1) * 100,
                     'risk_lock': False})
        equity = pd.DataFrame(rows).drop_duplicates('timestamp', keep='last').set_index('timestamp')
        trade_dicts = [asdict(t) for t in trades]
        metrics = self._metrics(trades, equity, cfg.initial_capital, capital, cfg.timeframe)
        metrics['confidence_calibration'] = calibrate_confidence(trade_dicts)
        metrics['monte_carlo'] = run_monte_carlo(trade_dicts, cfg.initial_capital,
                                                 cfg.monte_carlo_simulations)
        return BacktestResult(asdict(cfg), metrics, trade_dicts, equity)

    @staticmethod
    def _validated_config(cfg: BacktestConfig) -> BacktestConfig:
        if cfg.initial_capital <= 0:
            raise ValueError('El capital inicial debe ser positivo.')
        if not 0 < cfg.risk_per_trade <= .05:
            raise ValueError('El riesgo por operación debe estar entre 0 y 5%.')
        if not 0 < cfg.partial_fraction < 1:
            raise ValueError('La fracción parcial debe estar entre 0 y 1.')
        if cfg.partial_rr <= 0 or cfg.final_rr <= cfg.partial_rr:
            raise ValueError('Los objetivos R/R deben ser positivos y crecientes.')
        if cfg.market_type == 'spot' and cfg.allow_short:
            # Evita simular cortos imposibles en spot por accidente.
            return BacktestConfig(**{**asdict(cfg), 'allow_short': False})
        return cfg

    @staticmethod
    def _validate(data):
        required = {'open', 'high', 'low', 'close', 'volume'}
        if data is None:
            raise ValueError('No se recibieron datos OHLCV.')
        missing = required.difference(data.columns)
        if missing:
            raise ValueError(f'Faltan columnas OHLCV: {sorted(missing)}')
        df = data.copy().sort_index()
        for column in required:
            df[column] = pd.to_numeric(df[column], errors='coerce')
        df = df.dropna(subset=list(required))[~df.index.duplicated(keep='last')]
        invalid = (df['high'] < df[['open', 'close', 'low']].max(axis=1)) | \
                  (df['low'] > df[['open', 'close', 'high']].min(axis=1)) | \
                  (df[['open', 'high', 'low', 'close']] <= 0).any(axis=1) | (df['volume'] < 0)
        if invalid.any():
            raise ValueError(f'OHLCV contiene {int(invalid.sum())} velas inválidas.')
        return df

    def _open_position(self, signal, next_bar, entry_time, signal_time, decision,
                       capital, cfg, entry_index):
        side = 'LONG' if signal == 'BUY' else 'SHORT'
        raw = float(next_bar['open'])
        half = cfg.spread_rate / 2
        entry = raw * (1 + cfg.slippage_rate + half if side == 'LONG'
                       else 1 - cfg.slippage_rate - half)
        atr = max(float(decision.get('atr') or 0), entry * .002)
        plan = decision.get('trade_plan') or {}
        suggested_stop = float(plan.get('stop_loss') or 0)
        if side == 'LONG':
            distance = entry - suggested_stop if 0 < suggested_stop < entry else 1.5 * atr
            stop = entry - distance
            partial_target = entry + cfg.partial_rr * distance
            target = entry + cfg.final_rr * distance
        else:
            distance = suggested_stop - entry if suggested_stop > entry else 1.5 * atr
            stop = entry + distance
            partial_target = entry - cfg.partial_rr * distance
            target = entry - cfg.final_rr * distance
        if distance <= 0 or not math.isfinite(distance):
            return None
        risk_budget = max(0., capital * cfg.risk_per_trade)
        quantity = risk_budget / distance
        quantity = min(quantity, capital * cfg.max_notional_fraction / entry)
        if quantity * entry < cfg.min_trade_notional:
            return None
        return {'side': side, 'signal_time': signal_time, 'entry_time': entry_time,
                'entry': entry, 'stop': stop, 'initial_stop': stop,
                'partial_target': partial_target, 'target': target,
                'quantity': quantity, 'initial_quantity': quantity,
                'entry_index': entry_index,
                'confidence': float(decision.get('confidence', 0)),
                'score': float(decision.get('score', 0)),
                'regime': str((decision.get('market_regime') or {}).get('regime', 'desconocido')),
                'partial_realized': 0.0, 'partial_fees': 0.0,
                'partial_done': False, 'atr': atr}

    @staticmethod
    def _unrealized(position, price):
        direction = 1 if position['side'] == 'LONG' else -1
        return ((price - position['entry']) * position['quantity'] * direction
                + position.get('partial_realized', 0) - position.get('partial_fees', 0))

    def _execute_partial(self, position, raw_price, cfg):
        fraction = cfg.partial_fraction if cfg.partial_take_profit else 0
        quantity = position['quantity'] * fraction
        if quantity <= 0:
            return
        half = cfg.spread_rate / 2
        exit_price = raw_price * (1 - cfg.slippage_rate - half if position['side'] == 'LONG'
                                  else 1 + cfg.slippage_rate + half)
        direction = 1 if position['side'] == 'LONG' else -1
        gross = (exit_price - position['entry']) * quantity * direction
        fees = (position['entry'] + exit_price) * quantity * cfg.fee_rate
        position['partial_realized'] += gross
        position['partial_fees'] += fees
        position['quantity'] -= quantity
        position['partial_done'] = True
        if cfg.break_even_after_partial:
            fee_buffer = position['entry'] * cfg.fee_rate * 2
            position['stop'] = (position['entry'] + fee_buffer if position['side'] == 'LONG'
                                else position['entry'] - fee_buffer)

    def _update_trailing(self, position, bar, cfg):
        if not cfg.trailing_stop or not position.get('partial_done'):
            return
        distance = max(float(position['atr']) * cfg.trailing_atr_multiple,
                       abs(position['entry'] - position['initial_stop']) * .5)
        if position['side'] == 'LONG':
            position['stop'] = max(position['stop'], float(bar['close']) - distance)
        else:
            position['stop'] = min(position['stop'], float(bar['close']) + distance)

    def _check_exit(self, position, bar, timestamp, bar_index, cfg):
        o, h, l, c = map(float, (bar['open'], bar['high'], bar['low'], bar['close']))
        if position['side'] == 'LONG':
            if o <= position['stop']:
                return self._force_close(position, o, timestamp, bar_index, cfg, 'gap_stop')
            if o >= position['target']:
                return self._force_close(position, o, timestamp, bar_index, cfg, 'gap_objetivo')
            stop_hit, final_hit = l <= position['stop'], h >= position['target']
            partial_hit = h >= position['partial_target']
        else:
            if o >= position['stop']:
                return self._force_close(position, o, timestamp, bar_index, cfg, 'gap_stop')
            if o <= position['target']:
                return self._force_close(position, o, timestamp, bar_index, cfg, 'gap_objetivo')
            stop_hit, final_hit = h >= position['stop'], l <= position['target']
            partial_hit = l <= position['partial_target']

        # En una vela ambigua se usa la hipótesis adversa para evitar optimismo.
        if stop_hit and (final_hit or (partial_hit and not position['partial_done'])):
            return self._force_close(position, position['stop'], timestamp, bar_index, cfg,
                                     'stop_intrabar_conservador')
        if stop_hit:
            return self._force_close(position, position['stop'], timestamp, bar_index, cfg, 'stop_loss')
        if final_hit:
            return self._force_close(position, position['target'], timestamp, bar_index, cfg, 'take_profit_final')
        if cfg.partial_take_profit and partial_hit and not position['partial_done']:
            self._execute_partial(position, position['partial_target'], cfg)
        self._update_trailing(position, bar, cfg)
        if bar_index - position['entry_index'] >= cfg.max_bars_in_trade:
            return self._force_close(position, c, timestamp, bar_index, cfg, 'salida_por_tiempo')
        return None

    @staticmethod
    def _force_close(position, raw_exit, exit_time, exit_index, cfg, reason):
        half = cfg.spread_rate / 2
        exit_price = raw_exit * (1 - cfg.slippage_rate - half if position['side'] == 'LONG'
                                 else 1 + cfg.slippage_rate + half)
        direction = 1 if position['side'] == 'LONG' else -1
        gross_remaining = (exit_price - position['entry']) * position['quantity'] * direction
        fees_remaining = (position['entry'] + exit_price) * position['quantity'] * cfg.fee_rate
        gross = gross_remaining + position.get('partial_realized', 0)
        fees = fees_remaining + position.get('partial_fees', 0)
        net = gross - fees
        notional = position['entry'] * position['initial_quantity']
        return Trade(position['side'], str(position['signal_time']), str(position['entry_time']),
                     str(exit_time), position['entry'], exit_price, position['stop'],
                     position['target'], position['initial_quantity'], gross, fees, net,
                     net / notional * 100 if notional else 0,
                     max(1, exit_index - position['entry_index'] + 1), reason,
                     position['confidence'], position['score'], position['regime'],
                     position.get('partial_realized', 0) - position.get('partial_fees', 0))

    @staticmethod
    def _metrics(trades, equity, initial, final, timeframe):
        pnls = np.array([t.net_pnl for t in trades], float)
        wins, losses = pnls[pnls > 0], pnls[pnls < 0]
        total = len(trades)
        gross_profit = float(wins.sum()) if len(wins) else 0.
        gross_loss = abs(float(losses.sum())) if len(losses) else 0.
        profit_factor = gross_profit / gross_loss if gross_loss else (float('inf') if gross_profit else 0.)
        drawdown = abs(float(equity.drawdown_pct.min())) if len(equity) else 0.
        returns = equity.equity.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
        annual = ANNUAL_BARS.get(timeframe, 365)
        sharpe = float(np.sqrt(annual) * returns.mean() / returns.std()) if len(returns) > 2 and returns.std() > 0 else 0.
        downside = returns[returns < 0].std()
        sortino = float(np.sqrt(annual) * returns.mean() / downside) if pd.notna(downside) and downside > 0 else 0.
        streak = current = 0
        for pnl in pnls:
            current = current + 1 if pnl < 0 else 0
            streak = max(streak, current)
        return {
            'initial_capital': round(initial, 2), 'final_capital': round(final, 2),
            'net_profit': round(final - initial, 2),
            'net_return_pct': round((final / initial - 1) * 100, 2),
            'total_trades': total, 'winning_trades': int((pnls > 0).sum()),
            'losing_trades': int((pnls < 0).sum()),
            'win_rate_pct': round(float((pnls > 0).mean() * 100) if total else 0, 2),
            'profit_factor': round(profit_factor, 3) if math.isfinite(profit_factor) else '∞',
            'expectancy': round(float(pnls.mean()) if total else 0, 2),
            'average_win': round(float(wins.mean()) if len(wins) else 0, 2),
            'average_loss': round(float(losses.mean()) if len(losses) else 0, 2),
            'max_drawdown_pct': round(drawdown, 2), 'sharpe': round(sharpe, 3),
            'sortino': round(sortino, 3), 'sharpe_approx': round(sharpe, 3),
            'sortino_approx': round(sortino, 3), 'annualization_bars': annual,
            'recovery_factor': round((final - initial) / (initial * drawdown / 100), 3) if drawdown else 0.,
            'average_bars_held': round(float(np.mean([t.bars_held for t in trades])) if total else 0, 2),
            'max_consecutive_losses': int(streak),
            'partial_exit_trades': sum(bool(t.partial_pnl) for t in trades),
        }
