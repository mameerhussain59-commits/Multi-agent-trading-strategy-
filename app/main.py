from fastapi import FastAPI, HTTPException
from app.orchestrator import MasterAgent
from app.storage import save_scan, create_paper_trade, list_paper_trades
from app.monitor import monitor_open_trades
from app.backtest import backtest_binance
from app.config import settings

app=FastAPI(title='Multi-Agent Crypto Trader',version='0.4.0')
master=MasterAgent()

@app.get('/health')
async def health(): return {'status':'ok','mode':settings.trading_mode,'real_data_only':True}
@app.get('/api/discover')
async def discover(): return [t.model_dump(mode='json') for t in await master.hunter.run()]
@app.get('/api/scan')
async def scan(limit:int=30):
    if limit<1 or limit>50: raise HTTPException(400,'limit must be 1..50')
    results=await master.scan(limit); save_scan(results); return [x.model_dump(mode='json') for x in results]
@app.post('/api/paper/open/{symbol}')
async def open_paper(symbol:str):
    results=await master.scan(30); match=next((x for x in results if x.token.symbol.upper()==symbol.upper()),None)
    if not match: raise HTTPException(404,'No live-data scan available for token')
    if not match.trade.executable: raise HTTPException(400,'Trade does not pass signal/risk gates')
    trade_id=create_paper_trade(match.trade); return {'trade_id':trade_id,'trade':match.trade.model_dump(mode='json')}
@app.post('/api/paper/monitor')
async def paper_monitor(): return await monitor_open_trades()
@app.get('/api/paper/trades')
async def paper_trades(): return list_paper_trades()
@app.get('/api/backtest/{symbol}')
async def backtest(symbol:str, interval:str='1h', limit:int=1000):
    if interval not in {'1m','5m','15m','30m','1h','4h','1d'}: raise HTTPException(400,'unsupported interval')
    if limit<100 or limit>1000: raise HTTPException(400,'limit must be 100..1000')
    return await backtest_binance(symbol,interval,limit,settings.account_equity_usd,settings.risk_per_trade_pct)
