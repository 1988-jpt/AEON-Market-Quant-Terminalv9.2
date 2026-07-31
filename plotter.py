"""Gráficos profesionales de velas e indicadores con Matplotlib."""

import logging
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def save_candlestick_image(df: pd.DataFrame, path: str = 'chart.png',
                           levels: Optional[Dict] = None, symbol: str = '') -> str:
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
    except ImportError as exc:
        raise RuntimeError('Instala matplotlib para generar gráficos.') from exc

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = df.tail(140).copy().reset_index()
    x = range(len(frame))

    fig = plt.figure(figsize=(12, 8))
    grid = fig.add_gridspec(4, 1, height_ratios=[4, 1.2, 1.2, 1.2], hspace=0.08)
    ax_price = fig.add_subplot(grid[0])
    ax_volume = fig.add_subplot(grid[1], sharex=ax_price)
    ax_rsi = fig.add_subplot(grid[2], sharex=ax_price)
    ax_macd = fig.add_subplot(grid[3], sharex=ax_price)

    for i, row in frame.iterrows():
        rising = row['close'] >= row['open']
        fill = 'white' if rising else 'black'
        ax_price.vlines(i, row['low'], row['high'], linewidth=0.8)
        lower = min(row['open'], row['close'])
        height = max(abs(row['close'] - row['open']), 1e-9)
        ax_price.add_patch(Rectangle((i - 0.32, lower), 0.64, height,
                                     facecolor=fill, edgecolor='black', linewidth=0.7))

    for col in ('ema_9', 'ema_21', 'ema_50', 'bb_upper', 'bb_lower'):
        if col in frame.columns:
            ax_price.plot(list(x), frame[col], linewidth=1, label=col.upper())
    if levels:
        for value in levels.get('supports', []):
            ax_price.axhline(value, linestyle='--', linewidth=0.8)
        for value in levels.get('resistances', []):
            ax_price.axhline(value, linestyle=':', linewidth=0.8)

    ax_volume.bar(list(x), frame['volume'], width=0.7)
    if 'rsi' in frame.columns:
        ax_rsi.plot(list(x), frame['rsi'], linewidth=1)
        ax_rsi.axhline(70, linestyle='--', linewidth=0.7)
        ax_rsi.axhline(30, linestyle='--', linewidth=0.7)
        ax_rsi.set_ylim(0, 100)
    if 'macd' in frame.columns:
        ax_macd.plot(list(x), frame['macd'], linewidth=1, label='MACD')
    if 'macd_signal' in frame.columns:
        ax_macd.plot(list(x), frame['macd_signal'], linewidth=1, label='Señal')
    if 'macd_hist' in frame.columns:
        ax_macd.bar(list(x), frame['macd_hist'], width=0.7)

    ax_price.set_title(f'{symbol} - análisis técnico')
    ax_price.set_ylabel('Precio')
    ax_volume.set_ylabel('Volumen')
    ax_rsi.set_ylabel('RSI')
    ax_macd.set_ylabel('MACD')
    if ax_price.lines:
        ax_price.legend(loc='upper left', fontsize=8)
    if ax_macd.lines:
        ax_macd.legend(loc='upper left', fontsize=8)

    step = max(1, len(frame) // 8)
    ticks = list(range(0, len(frame), step))
    time_column = 'timestamp' if 'timestamp' in frame.columns else frame.columns[0]
    labels = [str(frame.iloc[i][time_column])[:16] for i in ticks]
    ax_macd.set_xticks(ticks)
    ax_macd.set_xticklabels(labels, rotation=25, ha='right', fontsize=8)
    for axis in (ax_price, ax_volume, ax_rsi):
        axis.tick_params(labelbottom=False)
    fig.tight_layout()
    fig.savefig(output, dpi=130, bbox_inches='tight')
    plt.close(fig)
    logger.info('Gráfico guardado en %s', output)
    return str(output)
