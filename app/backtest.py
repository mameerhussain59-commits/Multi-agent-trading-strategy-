from __future__ import annotations
from app.data import binance_klines
from app.technical import technical_analysis

def _num(v): return float(v)

async def backtest_binance(symbol: str, interval='1h', limit=1000, initial_equity=10000.0, risk_pct=0.5):
    pair=symbol.upper().replace('/','')+'USDT'
    rows=await binance_klines(pair,interval,min(limit,1000))
    if len(rows)<100: raise ValueError('Not enough real historical candles')
    equity=float(initial_equity); trades=[]; in_trade=None
    for i in range(60,len(rows)-1):
        closes=[_num(r[4]) for r in rows[:i]]; highs=[_num(r[2]) for r in rows[:i]]; lows=[_num(r[3]) for r in rows[:i]]
        tech=technical_analysis(symbol,closes,highs,lows,interval)
        if in_trade:
            candle=rows[i]; hi=_num(candle[2]); lo=_num(candle[3])
            exit_price=None; reason=None
            if lo<=in_trade['sl']: exit_price=in_trade['sl']; reason='SL'
            elif hi>=in_trade['tp']: exit_price=in_trade['tp']; reason='TP'
            if exit_price:
                pnl=(exit_price-in_trade['entry'])*in_trade['qty']; equity+=pnl
                trades.append({**in_trade,'exit':exit_price,'reason':reason,'pnl':pnl,'equity':equity}); in_trade=None
            continue
        if tech.trend!='bullish' or tech.rsi<50: continue
        entry=_num(rows[i+1][1]); sl=max(entry-2*tech.atr,entry*0.97); risk_per_unit=entry-sl
        if risk_per_unit<=0: continue
        risk_usd=equity*(risk_pct/100); qty=risk_usd/risk_per_unit; tp=entry+risk_per_unit*2.0
        in_trade={'entry':entry,'sl':sl,'tp':tp,'qty':qty,'opened_at':rows[i+1][0]}
    closed=[t for t in trades]
    wins=[t for t in closed if t['pnl']>0]; losses=[t for t in closed if t['pnl']<=0]
    return {'symbol':symbol,'pair':pair,'interval':interval,'candles':len(rows),'initial_equity':initial_equity,'final_equity':equity,'net_pnl':equity-initial_equity,'return_pct':(equity/initial_equity-1)*100,'trades':len(closed),'wins':len(wins),'losses':len(losses),'win_rate_pct':(len(wins)/len(closed)*100 if closed else 0),'data_source':'Binance historical klines'}
