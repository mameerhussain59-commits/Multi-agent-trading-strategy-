import asyncio
from app.data import mrnasdog_tokens, coingecko_markets, binance_klines
from app.models import Token, MarketSnapshot
from app.technical import technical_analysis
from app.risk import make_trade_plan, score_signal

class TokenHunterAgent:
    async def run(self):
        symbols=await mrnasdog_tokens()
        return [Token(symbol=s,source='mrnasdog') for s in symbols[:100]]

class MarketAgent:
    async def run(self, token):
        symbol=token.symbol.upper()+'USDT'
        try:
            rows=await binance_klines(symbol)
            closes=[float(r[4]) for r in rows]
            return symbol,closes
        except Exception:
            return None, None

class TechnicalAgent:
    def run(self, symbol, closes):
        return technical_analysis(symbol,closes)

class SignalAgent:
    def run(self, token, market, technical):
        s=score_signal(token.source_score, market.change_24h, technical.momentum_score)
        return s

class RiskAgent:
    def run(self, token, market, technical, score):
        return make_trade_plan(token.symbol,market.price,technical.atr,score,[technical.trend,'live market data'])

class MasterAgent:
    def __init__(self):
        self.hunter=TokenHunterAgent(); self.market=MarketAgent(); self.tech=TechnicalAgent(); self.signal=SignalAgent(); self.risk=RiskAgent()
    async def scan(self, limit=20):
        tokens=(await self.hunter.run())[:limit]; results=[]
        cg=await coingecko_markets(250)
        cgmap={str(x.get('symbol','')).upper():x for x in cg}
        for token in tokens:
            token.source_score=next((float(x.get('score')) for x in []),None)
            symbol,closes=await self.market.run(token)
            if not closes: continue
            c=cgmap.get(token.symbol.upper(),{})
            price=float(c.get('current_price') or closes[-1]); change=float(c.get('price_change_percentage_24h') or 0); volume=float(c.get('total_volume') or 0)
            market=MarketSnapshot(symbol=token.symbol,price=price,change_24h=change,volume_24h=volume,market_cap=c.get('market_cap'),source='coingecko+binance')
            tech=self.tech.run(token.symbol,closes); score=self.signal.run(token,market,tech)
            plan=self.risk.run(token,market,tech,score)
            results.append({'token':token.model_dump(),'market':market.model_dump(),'technical':tech.model_dump(),'trade':plan.model_dump()})
        return sorted(results,key=lambda x:x['trade']['score'],reverse=True)
