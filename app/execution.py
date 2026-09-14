from __future__ import annotations
import hashlib, hmac, time, urllib.parse, httpx
from app.config import settings

class ExecutionDisabled(RuntimeError): pass

class BinanceExecutor:
    """Authenticated executor. Disabled unless explicitly enabled and dry_run is false."""
    def __init__(self):
        self.base=settings.binance_base_url.rstrip('/')
        self.key=settings.binance_api_key; self.secret=settings.binance_api_secret
    def _signed(self, params):
        if not settings.live_trading_enabled or settings.dry_run or settings.trading_mode!='live':
            raise ExecutionDisabled('Live execution is disabled by safety configuration')
        if not self.key or not self.secret: raise ExecutionDisabled('Binance API credentials are missing')
        params=dict(params); params['timestamp']=int(time.time()*1000); params['recvWindow']=5000
        query=urllib.parse.urlencode(params); sig=hmac.new(self.secret.encode(),query.encode(),hashlib.sha256).hexdigest()
        return query+'&signature='+sig
    async def account(self):
        query=self._signed({})
        async with httpx.AsyncClient(timeout=settings.request_timeout) as c:
            r=await c.get(self.base+'/api/v3/account?'+query,headers={'X-MBX-APIKEY':self.key}); r.raise_for_status(); return r.json()
    async def market_buy(self,symbol,quantity):
        query=self._signed({'symbol':symbol,'side':'BUY','type':'MARKET','quantity':quantity})
        async with httpx.AsyncClient(timeout=settings.request_timeout) as c:
            r=await c.post(self.base+'/api/v3/order?'+query,headers={'X-MBX-APIKEY':self.key}); r.raise_for_status(); return r.json()
    async def market_sell(self,symbol,quantity):
        query=self._signed({'symbol':symbol,'side':'SELL','type':'MARKET','quantity':quantity})
        async with httpx.AsyncClient(timeout=settings.request_timeout) as c:
            r=await c.post(self.base+'/api/v3/order?'+query,headers={'X-MBX-APIKEY':self.key}); r.raise_for_status(); return r.json()
