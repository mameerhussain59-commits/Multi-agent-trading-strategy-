from app.models import TradePlan
from app.config import settings

def make_trade_plan(symbol, price, atr, score, reasons=None):
    reasons=reasons or []
    stop=max(price-2.0*atr, price*0.97)
    risk_per_unit=price-stop
    risk_usd=settings.account_equity_usd*(settings.risk_per_trade_pct/100)
    qty=risk_usd/risk_per_unit if risk_per_unit else 0
    max_qty=(settings.account_equity_usd*(settings.max_position_pct/100))/price
    qty=min(qty,max_qty)
    tp1=price+risk_per_unit*1.5; tp2=price+risk_per_unit*2.5; tp3=price+risk_per_unit*4
    return TradePlan(symbol=symbol,entry=price,stop_loss=stop,take_profit_1=tp1,take_profit_2=tp2,take_profit_3=tp3,risk_reward=(tp2-price)/risk_per_unit if risk_per_unit else 0,position_size=qty,risk_usd=qty*risk_per_unit,score=score,reasons=reasons,mode=settings.trading_mode)

def score_signal(source_score, market_change, technical_score, volume_ok=True):
    base=source_score or 0
    return max(0,min(100,base*7 + technical_score*0.25 + max(-10,min(10,market_change))*1.0 + (5 if volume_ok else -5)))
