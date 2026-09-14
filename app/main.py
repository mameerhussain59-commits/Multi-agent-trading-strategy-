from fastapi import FastAPI
from app.orchestrator import MasterAgent

app=FastAPI(title='Multi-Agent Crypto Trader',version='0.1.0')
master=MasterAgent()

@app.get('/health')
async def health(): return {'status':'ok','mode':'paper'}

@app.get('/api/discover')
async def discover():
    tokens=await master.hunter.run()
    return [t.model_dump() for t in tokens]

@app.get('/api/scan')
async def scan(limit:int=20):
    return await master.scan(limit)
