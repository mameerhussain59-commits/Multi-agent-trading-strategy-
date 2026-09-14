import asyncio, json, sys
from app.orchestrator import MasterAgent
from app.storage import save_scan, create_paper_trade, list_paper_trades

async def main():
    cmd=sys.argv[1] if len(sys.argv)>1 else 'scan'
    master=MasterAgent()
    if cmd=='discover':
        print(json.dumps([x.model_dump(mode='json') for x in await master.hunter.run()], indent=2))
    elif cmd=='scan':
        results=await master.scan(30); save_scan(results)
        print(json.dumps([x.model_dump(mode='json') for x in results], indent=2))
    elif cmd=='paper':
        results=await master.scan(30)
        opened=[]
        for result in results:
            if result.trade.executable:
                opened.append({'id':create_paper_trade(result.trade),'symbol':result.trade.symbol,'entry':result.trade.entry,'sl':result.trade.stop_loss,'tp1':result.trade.take_profit_1,'tp2':result.trade.take_profit_2,'tp3':result.trade.take_profit_3})
        print(json.dumps(opened, indent=2))
    elif cmd=='trades':
        print(json.dumps(list_paper_trades(), indent=2))
    else: raise SystemExit('use discover, scan, paper or trades')

if __name__=='__main__': asyncio.run(main())
