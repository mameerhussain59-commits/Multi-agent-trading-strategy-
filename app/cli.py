import asyncio
import sys
from app.orchestrator import MasterAgent

async def main():
    cmd=sys.argv[1] if len(sys.argv)>1 else 'scan'
    m=MasterAgent()
    if cmd=='discover':
        for x in await m.hunter.run(): print(x.symbol)
    elif cmd in ('scan','paper'):
        import json
        print(json.dumps(await m.scan(25),indent=2,default=str))
    else: raise SystemExit('use discover, scan or paper')

if __name__=='__main__': asyncio.run(main())
