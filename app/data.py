from __future__ import annotations
from datetime import datetime, timezone
import re, time, xml.etree.ElementTree as ET
import httpx
from bs4 import BeautifulSoup
from app.config import settings


def now(): return datetime.now(timezone.utc)


class DataError(RuntimeError): pass


class HTTP:
    async def get(self, url, params=None, headers=None):
        async with httpx.AsyncClient(timeout=settings.request_timeout, follow_redirects=True) as client:
            r = await client.get(url, params=params, headers=headers)
            r.raise_for_status()
            return r


http = HTTP()
_CG_CACHE: tuple[float, list[dict]] | None = None


async def _research_urls():
    """Use the public homepage first, then sitemap if available. No hardcoded token universe."""
    urls = []
    try:
        home = await http.get(settings.mrnasdog_url)
        soup = BeautifulSoup(home.text, 'html.parser')
        urls += [a.get('href') for a in soup.find_all('a', href=True) if '/research/' in a.get('href', '')]
    except Exception:
        pass
    try:
        sitemap = await http.get(settings.mrnasdog_sitemap_url)
        root = ET.fromstring(sitemap.text)
        urls += [el.text for el in root.iter() if el.tag.endswith('loc') and el.text and '/research/' in el.text.lower()]
    except Exception:
        pass
    out = []
    for u in urls:
        if u.startswith('/'): u = 'https://mrnasdog.com' + u
        if u not in out: out.append(u)
    return out


async def mrnasdog_scored_tokens():
    """Read actual scored research pages. Inflation-only pages are rejected."""
    results = []
    for url in (await _research_urls())[:settings.max_research_pages]:
        try:
            r = await http.get(url)
            soup = BeautifulSoup(r.text, 'html.parser')
            text = soup.get_text(' ', strip=True)
            score_match = re.search(r'(?:MrNasdog\s+score|Score\s*\(0.?10\)|score).*?\b(\d+(?:\.\d+)?)\s*/\s*10\b', text, re.I)
            if not score_match: continue
            score = float(score_match.group(1))
            if not 0 <= score <= 10: continue
            title = soup.title.get_text(' ', strip=True) if soup.title else ''
            symbol_match = re.search(r'\b([A-Z][A-Z0-9]{1,9})\b', title)
            if not symbol_match: symbol_match = re.search(r'/research/([a-z0-9-]+)', url, re.I)
            if not symbol_match: continue
            raw = symbol_match.group(1)
            symbol = raw.split('-')[0].upper()
            results.append({'symbol': symbol, 'score': score, 'url': url, 'observed_at': now().isoformat()})
        except Exception:
            continue
    unique = {item['symbol']: item for item in results}
    return sorted(unique.values(), key=lambda x: x['score'], reverse=True)


async def dexscreener_search(query):
    r = await http.get('https://api.dexscreener.com/latest/dex/search', {'q': query})
    return r.json()


async def dexscreener_token(symbol):
    data = await dexscreener_search(symbol)
    pairs = [p for p in (data.get('pairs') or []) if p.get('priceUsd')]
    pairs.sort(key=lambda p: float(p.get('liquidity', {}).get('usd') or 0), reverse=True)
    return pairs[0] if pairs else None


async def coingecko_markets(limit=250):
    global _CG_CACHE
    cache_ttl = 60.0
    if _CG_CACHE is not None and time.monotonic() - _CG_CACHE[0] < cache_ttl:
        return _CG_CACHE[1]
    headers = {'accept': 'application/json'}
    if settings.coingecko_api_key: headers['x-cg-demo-api-key'] = settings.coingecko_api_key
    r = await http.get(
        'https://api.coingecko.com/api/v3/coins/markets',
        {'vs_currency': 'usd', 'order': 'market_cap_desc', 'per_page': min(limit, 250), 'page': 1, 'sparkline': 'false', 'price_change_percentage': '24h'},
        headers=headers,
    )
    data = r.json()
    if not isinstance(data, list): raise DataError('CoinGecko returned an invalid market response')
    _CG_CACHE = (time.monotonic(), data)
    return data


async def coingecko_coin(symbol):
    matches = [x for x in await coingecko_markets(250) if str(x.get('symbol', '')).upper() == symbol.upper()]
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
    if data.get('retCode') != 0: raise DataError(data.get('retMsg', 'Bybit error'))
    return data


async def bybit_klines(symbol, interval='60', limit=200):
    r = await http.get('https://api.bybit.com/v5/market/kline', {'category': 'spot', 'symbol': symbol, 'interval': interval, 'limit': limit})
    data = r.json()
    if data.get('retCode') != 0: raise DataError(data.get('retMsg', 'Bybit error'))
    return data['result']['list']


async def bybit_order_book(symbol, limit=20):
    r = await http.get('https://api.bybit.com/v5/market/orderbook', {'category': 'spot', 'symbol': symbol, 'limit': limit})
    data = r.json()
    if data.get('retCode') != 0: raise DataError(data.get('retMsg', 'Bybit error'))
    return data['result']


async def live_market(symbol):
    pair = symbol.upper().replace('/', '') + 'USDT'
    try:
        t = await binance_ticker(pair)
        candles = await binance_klines(pair)
        ob = await binance_order_book(pair)
        if not candles or float(t['lastPrice']) <= 0: raise DataError('Binance returned incomplete market data')
        return {'exchange': 'binance', 'pair': pair, 'price': float(t['lastPrice']), 'change_24h': float(t['priceChangePercent']), 'volume_24h': float(t['quoteVolume']), 'high_24h': float(t['highPrice']), 'low_24h': float(t['lowPrice']), 'candles': candles, 'order_book': ob, 'observed_at': now().isoformat()}
    except Exception as be:
        try:
            t = await bybit_ticker(pair)
            item = t['result']['list'][0]
            candles = list(reversed(await bybit_klines(pair)))
            ob = await bybit_order_book(pair)
            if not candles or float(item['lastPrice']) <= 0: raise DataError('Bybit returned incomplete market data')
            return {'exchange': 'bybit', 'pair': pair, 'price': float(item['lastPrice']), 'change_24h': float(item.get('price24hPcnt', 0)) * 100, 'volume_24h': float(item.get('turnover24h', 0)), 'high_24h': float(item.get('highPrice24h', 0)), 'low_24h': float(item.get('lowPrice24h', 0)), 'candles': [[r[0], r[1], r[2], r[3], r[4]] for r in candles], 'order_book': ob, 'observed_at': now().isoformat()}
        except Exception as ye:
            raise DataError(f'No live exchange data for {symbol}: Binance={be}; Bybit={ye}')
