"""Estrategia técnica multifactor explicable, conservadora y sin IA."""
from __future__ import annotations

from typing import Any, Dict, Optional
import math
import pandas as pd

from candlestick_patterns import detect_patterns
from market_context import classify_regime, detect_divergence, higher_timeframe_bias
from risk_management import build_trade_plan
from support_resistance import calculate_levels
from technical_indicators import add_quality_indicators
from futures_context import score_derivatives


class AdvancedStrategy:
    """Genera señales solo cuando existen confirmaciones independientes suficientes."""

    def decide(self, df: pd.DataFrame, news_sentiment: float = 0.0,
               higher_timeframe_df: Optional[pd.DataFrame] = None,
               derivatives_context=None) -> Dict[str, Any]:
        required = {'ema_9','ema_21','ema_50','sma_200','rsi','macd','macd_signal',
                    'macd_hist','atr','adx','plus_di','minus_di','stoch_k','vwap',
                    'obv','obv_ema','volume_ratio','efficiency_ratio','atr_pct'}
        # El backtester puede entregar indicadores precalculados. Todos son causales
        # (rolling/ewm solo usan pasado), por lo que no introduce look-ahead.
        analyzed = df if required.issubset(df.columns) else add_quality_indicators(df)
        higher = None
        if higher_timeframe_df is not None:
            higher = higher_timeframe_df if required.issubset(higher_timeframe_df.columns) else add_quality_indicators(higher_timeframe_df)
        last, previous = analyzed.iloc[-1], analyzed.iloc[-2]
        context = classify_regime(analyzed)
        divergence = detect_divergence(analyzed)
        mtf = higher_timeframe_bias(higher)
        levels = calculate_levels(analyzed)
        patterns = detect_patterns(analyzed)

        long_score = 0.0
        short_score = 0.0
        long_reasons, short_reasons, warnings = [], [], []

        # Tendencia y estructura: mayor peso.
        if last['ema_9'] > last['ema_21'] > last['ema_50']:
            long_score += 2.0; long_reasons.append('EMA 9/21/50 alineadas al alza')
        elif last['ema_9'] < last['ema_21'] < last['ema_50']:
            short_score += 2.0; short_reasons.append('EMA 9/21/50 alineadas a la baja')
        if not math.isnan(float(last['sma_200'])):
            if last['close'] > last['sma_200']:
                long_score += 0.75
            else:
                short_score += 0.75

        # Impulso: exige cruce o aceleración, no solo signo.
        macd_cross_up = previous['macd'] <= previous['macd_signal'] and last['macd'] > last['macd_signal']
        macd_cross_down = previous['macd'] >= previous['macd_signal'] and last['macd'] < last['macd_signal']
        if macd_cross_up or (last['macd_hist'] > previous['macd_hist'] > 0):
            long_score += 1.4; long_reasons.append('MACD acelera al alza')
        if macd_cross_down or (last['macd_hist'] < previous['macd_hist'] < 0):
            short_score += 1.4; short_reasons.append('MACD acelera a la baja')
        if 48 <= last['rsi'] <= 66:
            long_score += 0.8
        elif 34 <= last['rsi'] <= 52:
            short_score += 0.8
        if last['rsi'] >= 72:
            long_score -= 1.0; warnings.append('RSI sobrecomprado')
        if last['rsi'] <= 28:
            short_score -= 1.0; warnings.append('RSI sobrevendido')

        # Fuerza, volumen y participación.
        if last['adx'] >= 23:
            if last['plus_di'] > last['minus_di']:
                long_score += 1.0
            else:
                short_score += 1.0
        else:
            warnings.append('ADX débil')
        if last['volume_ratio'] >= 1.15:
            if last['close'] >= last['open']:
                long_score += 0.8; long_reasons.append('Volumen confirma presión compradora')
            else:
                short_score += 0.8; short_reasons.append('Volumen confirma presión vendedora')
        elif last['volume_ratio'] < 0.7:
            warnings.append('Volumen insuficiente')
        if last['obv'] > last['obv_ema']:
            long_score += 0.45
        else:
            short_score += 0.45
        if last['close'] > last['vwap']:
            long_score += 0.6
        else:
            short_score += 0.6

        # Régimen de mercado y eficiencia.
        if context['regime'] == 'tendencia_alcista':
            long_score += 1.2
        elif context['regime'] == 'tendencia_bajista':
            short_score += 1.2
        elif context['regime'] == 'lateral':
            long_score -= 0.8; short_score -= 0.8; warnings.append('Mercado lateral')
        if last['efficiency_ratio'] < 0.22:
            long_score -= 0.5; short_score -= 0.5; warnings.append('Movimiento poco eficiente')
        if context['volatility'] == 'extrema':
            long_score -= 1.0; short_score -= 1.0; warnings.append('Volatilidad extrema')

        # Confirmación temporal superior.
        if mtf['bias'] == 'alcista':
            long_score += 1.5; short_score -= 0.8; long_reasons.append('Temporalidad superior alcista')
        elif mtf['bias'] == 'bajista':
            short_score += 1.5; long_score -= 0.8; short_reasons.append('Temporalidad superior bajista')
        else:
            warnings.append('Temporalidad superior sin dirección clara')

        # Patrones y divergencias.
        bullish = {'Martillo', 'Envolvente alcista', 'Estrella de la mañana'}
        bearish = {'Estrella fugaz', 'Envolvente bajista', 'Estrella de la tarde'}
        long_score += 0.65 * sum(p in bullish for p in patterns)
        short_score += 0.65 * sum(p in bearish for p in patterns)
        if divergence == 'alcista':
            long_score += 1.0; long_reasons.append('Divergencia alcista de RSI')
        elif divergence == 'bajista':
            short_score += 1.0; short_reasons.append('Divergencia bajista de RSI')

        # Microestructura y derivados: peso limitado y explicable; nunca domina la señal.
        derivative_score = score_derivatives(derivatives_context)
        long_score += derivative_score['long']; short_score += derivative_score['short']
        warnings.extend(derivative_score['warnings'])
        long_reasons.extend(derivative_score['reasons_long'])
        short_reasons.extend(derivative_score['reasons_short'])

        # Noticias: peso limitado para que no domine el análisis técnico.
        sentiment = max(-1.0, min(1.0, float(news_sentiment)))
        if sentiment > 0:
            long_score += sentiment * 0.6
        elif sentiment < 0:
            short_score += abs(sentiment) * 0.6

        # Evita señales donde ambos lados tienen evidencia similar.
        edge = long_score - short_score
        best_score = max(long_score, short_score)
        minimum = 5.2
        if best_score < minimum or abs(edge) < 1.8:
            signal = 'HOLD'
        elif edge > 0:
            signal = 'BUY'
        else:
            signal = 'SELL'

        # Penalizaciones duras de calidad.
        if context['volatility'] == 'extrema' or last['volume_ratio'] < 0.55:
            signal = 'HOLD'
        if signal == 'BUY' and mtf['bias'] == 'bajista':
            signal = 'HOLD'
        if signal == 'SELL' and mtf['bias'] == 'alcista':
            signal = 'HOLD'

        agreement = abs(edge) / max(long_score + short_score, 1.0)
        confidence = 50.0 if signal == 'HOLD' else min(92.0, 58.0 + best_score * 3.2 + agreement * 12)
        selected_reasons = long_reasons if signal == 'BUY' else short_reasons if signal == 'SELL' else warnings
        reason = '; '.join(selected_reasons[:6]) or 'No existen confirmaciones independientes suficientes.'
        plan = build_trade_plan(signal, float(last['close']), float(last['atr']),
                                levels.get('supports', []), levels.get('resistances', []))

        return {
            'signal': signal, 'reason': reason,
            'score': round(edge, 2), 'long_score': round(long_score, 2),
            'short_score': round(short_score, 2), 'confidence': round(confidence, 1),
            'rsi': float(last['rsi']), 'macd': float(last['macd']),
            'macd_signal': float(last['macd_signal']), 'adx': float(last['adx']),
            'atr': float(last['atr']), 'stoch_k': float(last['stoch_k']),
            'vwap': float(last['vwap']), 'volume_ratio': float(last['volume_ratio']),
            'efficiency_ratio': float(last['efficiency_ratio']),
            'patterns': patterns, 'divergence': divergence,
            'market_regime': context, 'higher_timeframe': mtf,
            'warnings': warnings, 'trade_plan': plan,
            'derivatives_context': derivatives_context.__dict__ if derivatives_context is not None else None,
            **levels, 'dataframe': analyzed,
        }
