import asyncio,json,sys
from app.orchestrator import MasterAgent
from app.storage import save_scan,create_paper_trade,list_paper_trades
from app.monitor import monitor_open_trades
from app.backtest import backtest_binance
from app.config import settings

async def main():
    cmd=sys.argv[1] if len(sys.argv)>1 else 'scan'; master=MasterAgent()
    if cmd=='discover': print(json.dumps([x.model_dump(mode='json') for x in await master.hunter.run()],indent=2))
    elif cmd=='scan':
        results=await master.scan(30); save_scan(results); print(json.dumps([x.model_dump(mode='json') for x in results],indent=2))
    elif cmd=='paper':
        results=await master.scan(30); opened=[]
        for r in results:
            if r.trade.executable: opened.append({'id':create_paper_trade(r.trade),'symbol':r.trade.symbol,'entry':r.trade.entry,'sl':r.trade.stop_loss,'tp1':r.trade.take_profit_1,'tp2':r.trade.take_profit_2,'tp3':r.trade.take_profit_3})
        print(json.dumps(opened,indent=2))
    elif cmd=='monitor': print(json.dumps(await monitor_open_trades(),indent=2))
    elif cmd=='trades': print(json.dumps(list_paper_trades(),indent=2))
    elif cmd=='backtest':
        if len(sys.argv)<3: raise SystemExit('use: python -m app.cli backtest BTC')
        print(json.dumps(await backtest_binance(sys.argv[2],initial_equity=settings.account_equity_usd,risk_pct=settings.risk_per_trade_pct),indent=2))
    else: raise SystemExit('use discover, scan, paper, monitor, trades or backtest SYMBOL')
if __name__=='__main__': asyncio.run(main())
