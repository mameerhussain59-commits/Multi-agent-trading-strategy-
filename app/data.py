from __future__ import annotations

from datetime import datetime, timezone
import re
import xml.etree.ElementTree as ET
import httpx
from bs4 import BeautifulSoup
from app.config import settings


def now() -> datetime:
    return datetime.now(timezone.utc)


class DataError(RuntimeError):
    pass


class HTTP:
    async def get(self, url: str, params=None, headers=None):
        async with httpx.AsyncClient(timeout=settings.request_timeout, follow_redirects=True) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response


http = HTTP()


async def mrnasdog_scored_tokens() -> list[dict]:
    """Discover scored research pages live; never invent a token list."""
    sitemap = await http.get(settings.mrnasdog_sitemap_url)
    root = ET.fromstring(sitemap.text)
    urls = [el.text for el in root.iter() if el.tag.endswith('loc') and el.text]
    candidates = [u for u in urls if '/research/' in u.lower() or '/token/' in u.lower()]
    results = []
    for url in candidates[:settings.max_research_pages]:
        try:
            r = await http.get(url)
            soup = BeautifulSoup(r.text, 'html.parser')
            text = soup.get_text(' ', strip=True)
            title = soup.title.get_text(' ', strip=True) if soup.title else ''
            # Accept only explicit score statements. This avoids treating random uppercase words as symbols.
            m = re.search(r'\b(\d+(?:\.\d+)?)\s*/\s*10\b', text)
            if not m:
                continue
            score = float(m.group(1))
            if not 0 <= score <= 10:
                continue
            symbol = None
            for pattern in (r'\b([A-Z][A-Z0-9]{1,9})\s+(?:score|analysis|research)\b', r'\b(?:score|research)\s+(?:for\s+)?([A-Z][A-Z0-9]{1,9})\b'):
                hit = re.search(pattern, text, re.I)
                if hit:
                    symbol = hit.group(1).upper(); break
            if not symbol:
                # Research pages commonly expose the ticker in the title.
                hits = re.findall(r'\b[A-Z][A-Z0-9]{1,9}\b', title)
                deny = {'THE','AND','FOR','WITH','COIN','TOKEN','SCORE','RESEARCH'}
                hits = [h for h in hits if h not in deny]
                symbol = hits[0] if hits else None
            if symbol:
                results.append({'symbol': symbol, 'score': score, 'url': url, 'observed_at': now().isoformat()})
        except Exception:
            continue
    unique = {}
    for item in results:
        unique[item['symbol']] = item
    return sorted(unique.values(), key=lambda x: x['score'], reverse=True)


async def dexscreener_search(query: str):
    r = await http.get('https://api.dexscreener.com/latest/dex/search', {'q': query})
    return r.json()


async def dexscreener_token(symbol: str):
    data = await dexscreener_search(symbol)
    pairs = data.get('pairs') or []
    pairs = [p for p in pairs if p.get('priceUsd')]
    pairs.sort(key=lambda p: float(p.get('liquidity', {}).get('usd') or 0), reverse=True)
    return pairs[0] if pairs else None


async def coingecko_markets(limit=250):
    headers = {'accept': 'application/json'}
    if settings.coingecko_api_key:
        headers['x-cg-demo-api-key'] = settings.coingecko_api_key
    r = await http.get('https://api.coingecko.com/api/v3/coins/markets', {
        'vs_currency': 'usd', 'order': 'market_cap_desc', 'per_page': min(limit, 250),
        'page': 1, 'sparkline': 'false', 'price_change_percentage': '24h'
    }, headers=headers)
    return r.json()


async def coingecko_coin(symbol: str):
    markets = await coingecko_markets(250)
    matches = [x for x in markets if str(x.get('symbol','')).upper() == symbol.upper()]
    return max(matches, key=lambda x: float(x.get('market_cap') or 0), default=None)


async def binance_ticker(symbol):
    r = await http.get('https://api.binance.com/api/v3/ticker/24hr', {'symbol': symbol})
    return r.json()


async def binance_klines(symbol, interval='1h', limit=200):
    r = await http.get('https://api.binance.com/api/v3/klines', {'symbol': symbol, 'interval': interval, 'limit': limit})
    return r.json()


async def binance_order_book(symbol, limit=20):
    r = await http.get('https://api.binance.com/api/v3/depth', {'symbol': symbol, 'limit': limit})
    return r.json()


async def bybit_ticker(symbol, category='spot'):
    r = await http.get('https://api.bybit.com/v5/market/tickers', {'category': category, 'symbol': symbol})
    data = r.json()
    if data.get('retCode') != 0:
        raise DataError(data.get('retMsg', 'Bybit error'))
    return data


async def bybit_klines(symbol, interval='60', limit=200):
    r = await http.get('https://api.bybit.com/v5/market/kline', {'category': 'spot', 'symbol': symbol, 'interval': interval, 'limit': limit})
    data = r.json()
    if data.get('retCode') != 0:
        raise DataError(data.get('retMsg', 'Bybit error'))
    return data['result']['list']


async def live_market(symbol: str) -> dict:
    """Prefer Binance, then Bybit; price is always exchange-observed."""
    pair = symbol.upper().replace('/', '') + 'USDT'
    try:
        ticker = await binance_ticker(pair)
        candles = await binance_klines(pair)
        orderbook = await binance_order_book(pair)
        return {'exchange': 'binance', 'pair': pair, 'price': float(ticker['lastPrice']),
                'change_24h': float(ticker['priceChangePercent']), 'volume_24h': float(ticker['quoteVolume']),
                'high_24h': float(ticker['highPrice']), 'low_24h': float(ticker['lowPrice']),
                'candles': candles, 'order_book': orderbook, 'observed_at': now().isoformat()}
    except Exception as binance_error:
        try:
            ticker = await bybit_ticker(pair)
            item = ticker['result']['list'][0]
            candles = await bybit_klines(pair)
            closes = [float(row[4]) for row in reversed(candles)]
            return {'exchange': 'bybit', 'pair': pair, 'price': float(item['lastPrice']),
                    'change_24h': float(item.get('price24hPcnt', 0))*100, 'volume_24h': float(item.get('turnover24h', 0)),
                    'high_24h': float(item.get('highPrice24h', 0)), 'low_24h': float(item.get('lowPrice24h', 0)),
                    'candles': [[0,0,0,0,c] for c in closes], 'order_book': None, 'observed_at': now().isoformat()}
        except Exception as bybit_error:
            raise DataError(f'No live exchange data for {symbol}: Binance={binance_error}; Bybit={bybit_error}')
