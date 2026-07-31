"""Noticias públicas mediante RSS y análisis léxico de sentimiento."""

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import List
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import requests

logger = logging.getLogger(__name__)

POSITIVE = {'surge','rally','gain','bullish','approval','adoption','record','growth','positive','sube','alza','alcista','aprobación','adopción','crecimiento','récord'}
NEGATIVE = {'drop','fall','crash','bearish','hack','fraud','ban','loss','negative','baja','cae','desplome','bajista','hackeo','fraude','prohibición','pérdida'}

@dataclass(frozen=True)
class NewsItem:
    title: str
    link: str
    published: str
    score: float


def score_text(text: str) -> float:
    words = re.findall(r"[a-záéíóúñ]+", text.lower())
    if not words:
        return 0.0
    pos = sum(w in POSITIVE for w in words)
    neg = sum(w in NEGATIVE for w in words)
    return max(-1.0, min(1.0, (pos - neg) / max(pos + neg, 1)))


def _fetch_sync(query: str, limit: int) -> List[NewsItem]:
    url = f'https://news.google.com/rss/search?q={quote_plus(query)}&hl=es-419&gl=US&ceid=US:es-419'
    response = requests.get(url, timeout=12, headers={'User-Agent': 'MarketAnalyzer/1.0'})
    response.raise_for_status()
    root = ET.fromstring(response.content)
    items = []
    for item in root.findall('.//item')[:limit]:
        title = item.findtext('title', default='Sin título').strip()
        items.append(NewsItem(title, item.findtext('link', default=''), item.findtext('pubDate', default=''), score_text(title)))
    return items


async def fetch_news(symbol: str, limit: int = 8) -> List[NewsItem]:
    asset = symbol.split('/')[0].upper()
    query = f'{asset} criptomoneda OR crypto'
    try:
        return await asyncio.to_thread(_fetch_sync, query, limit)
    except Exception as exc:
        logger.warning('No se pudieron descargar noticias: %s', exc)
        return []


def summarize_sentiment(items: List[NewsItem]) -> dict:
    if not items:
        return {'score': 0.0, 'label': 'Neutral', 'count': 0}
    score = sum(x.score for x in items) / len(items)
    label = 'Muy positivo' if score >= .5 else 'Positivo' if score >= .15 else 'Muy negativo' if score <= -.5 else 'Negativo' if score <= -.15 else 'Neutral'
    return {'score': round(score, 3), 'label': label, 'count': len(items)}
