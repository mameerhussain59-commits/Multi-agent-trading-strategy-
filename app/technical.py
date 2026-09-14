import numpy as np
from app.models import TechnicalSnapshot

def technical_analysis(symbol, closes):
    x=np.asarray(closes,dtype=float)
    if len(x)<60: raise ValueError('Need at least 60 candles')
    d=np.diff(x); gain=np.maximum(d,0); loss=np.maximum(-d,0)
    ag=gain[-14:].mean(); al=loss[-14:].mean(); rs=ag/al if al else 100
    rsi=100-(100/(1+rs))
    ema_fast=float(np.mean(x[-20:])); ema_slow=float(np.mean(x[-50:]))
    atr=float(np.mean(np.abs(np.diff(x))[-14:]))
    trend='bullish' if ema_fast>ema_slow and rsi>=50 else 'bearish' if ema_fast<ema_slow and rsi<50 else 'neutral'
    momentum=max(0,min(100,50+(rsi-50)*1.2))
    return TechnicalSnapshot(symbol=symbol,rsi=rsi,ema_fast=ema_fast,ema_slow=ema_slow,atr=atr,trend=trend,momentum_score=momentum)
