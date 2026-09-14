import numpy as np
from app.models import TechnicalSnapshot


def _ema(x, span):
    alpha = 2 / (span + 1)
    value = float(x[0])
    for item in x[1:]:
        value = alpha * float(item) + (1-alpha) * value
    return value


def technical_analysis(symbol, closes, highs=None, lows=None, timeframe='1h'):
    x = np.asarray(closes, dtype=float)
    if len(x) < 60:
        raise ValueError('Need at least 60 real candles')
    d = np.diff(x)
    gain = np.maximum(d, 0)
    loss = np.maximum(-d, 0)
    ag = float(gain[-14:].mean())
    al = float(loss[-14:].mean())
    rs = ag / al if al > 0 else 100.0
    rsi = 100 - (100 / (1 + rs))
    ema_fast = _ema(x, 20)
    ema_slow = _ema(x, 50)
    if highs is not None and lows is not None and len(highs) == len(x):
        h, l = np.asarray(highs, dtype=float), np.asarray(lows, dtype=float)
        prev = np.roll(x, 1); prev[0] = x[0]
        tr = np.maximum(h-l, np.maximum(abs(h-prev), abs(l-prev)))
        atr = float(tr[-14:].mean())
    else:
        atr = float(np.mean(np.abs(np.diff(x))[-14:]))
    trend = 'bullish' if ema_fast > ema_slow and rsi >= 50 else 'bearish' if ema_fast < ema_slow and rsi < 50 else 'neutral'
    momentum = max(0, min(100, 50 + (rsi-50)*1.2))
    return TechnicalSnapshot(symbol=symbol, timeframe=timeframe, rsi=float(rsi), ema_fast=ema_fast,
                             ema_slow=ema_slow, atr=max(atr, x[-1]*0.0001), trend=trend,
                             momentum_score=float(momentum))
