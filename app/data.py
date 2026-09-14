from datetime import datetime, timezone
import httpx
from bs4 import BeautifulSoup
from app.config import settings

def now(): return datetime.now(timezone.utc)

class HTTP:
    async def get(self, url, params=None, headers=None):
        async with httpx.AsyncClient(timeout=settings.request_timeout, follow_redirects=True) as c:
            r = await c.get(url, params=params, headers=headers); r.raise_for_status(); return r

http = HTTP()

async def mrnasdog_page():
    r = await http.get(settings.mrnasdog_url)
    return r.text

async def mrnasdog_tokens():
    html = await mrnasdog_page()
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(' ', strip=True)
    # The site changes its HTML frequently. Extract symbols from common score-card patterns.
    import re
    symbols = set(re.findall(r'\b[A-Z][A-Z0-9]{1,9}\b', text))
    deny={'USD','USDT','API','THE','AND','FOR','BTC'}
    return sorted(s for s in symbols if s not in deny)

async def dexscreener_search(query: str):
    r = await http.get('https://api.dexscreener.com/latest/dex/search', {'q': query})
    return r.json()

async def coingecko_markets(limit=100):
    headers = {}
    if settings.coingecko_api_key: headers['x-cg-demo-api-key'] = settings.coingecko_api_key
    r = await http.get('https://api.coingecko.com/api/v3/coins/markets', {
        'vs_currency':'usd','order':'market_cap_desc','per_page':limit,'page':1,'sparkline':'false'
    }, headers=headers)
    return r.json()

async def binance_ticker(symbol):
    r = await http.get('https://api.binance.com/api/v3/ticker/24hr', {'symbol':symbol})
    return r.json()

async def binance_klines(symbol, interval='1h', limit=200):
    r = await http.get('https://api.binance.com/api/v3/klines', {'symbol':symbol,'interval':interval,'limit':limit})
    return r.json()

async def bybit_ticker(symbol, category='spot'):
    r = await http.get('https://api.bybit.com/v5/market/tickers', {'category':category,'symbol':symbol})
    return r.json()
