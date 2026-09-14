from app.models import TradePlan
from app.config import settings


def make_trade_plan(symbol, price, atr, score, reasons=None, warnings=None):
    reasons = reasons or []
    warnings = warnings or []
    if price <= 0 or atr <= 0:
        raise ValueError('Invalid live price/ATR')
    stop = max(price - 2.0 * atr, price * 0.97)
    risk_per_unit = price - stop
    risk_usd = settings.account_equity_usd * (settings.risk_per_trade_pct / 100)
    qty = risk_usd / risk_per_unit
    max_qty = (settings.account_equity_usd * (settings.max_position_pct / 100)) / price
    qty = min(qty, max_qty)
    tp1 = price + risk_per_unit * 1.5
    tp2 = price + risk_per_unit * 2.5
    tp3 = price + risk_per_unit * 4.0
    executable = score >= settings.min_signal_score and settings.trading_mode == 'paper'
    if score < settings.min_signal_score:
        warnings.append(f'Signal score {score:.1f} below minimum {settings.min_signal_score:.1f}')
    return TradePlan(symbol=symbol, entry=price, stop_loss=stop, take_profit_1=tp1,
                     take_profit_2=tp2, take_profit_3=tp3,
                     risk_reward=(tp2-price)/risk_per_unit, position_size=qty,
                     risk_usd=qty*risk_per_unit, score=score, executable=executable,
                     reasons=reasons, warnings=warnings, mode=settings.trading_mode)


def score_signal(source_score, market_change, technical_score, volume_ok=True, liquidity_ok=True):
    # Source research is one input only; live market structure carries most weight.
    research = max(0.0, min(100.0, (source_score or 0) * 10))
    momentum = max(0.0, min(100.0, technical_score))
    momentum_change = max(0.0, min(100.0, 50 + float(market_change) * 2))
    score = research * 0.35 + momentum * 0.35 + momentum_change * 0.20
    score += 10 if volume_ok and liquidity_ok else -10
    return max(0.0, min(100.0, score))
