from app.data import live_market
from app.storage import open_paper_trades, close_paper_trade

async def monitor_open_trades():
    events=[]
    for trade in open_paper_trades():
        live=await live_market(trade['symbol'])
        price=float(live['price']); plan=trade['payload']
        reason=None
        if price <= float(plan['stop_loss']): reason='STOP_LOSS'
        elif price >= float(plan['take_profit_3']): reason='TAKE_PROFIT_3'
        elif price >= float(plan['take_profit_2']): reason='TAKE_PROFIT_2'
        elif price >= float(plan['take_profit_1']): reason='TAKE_PROFIT_1'
        if reason:
            pnl=close_paper_trade(trade['id'],price,reason)
            events.append({'trade_id':trade['id'],'symbol':trade['symbol'],'price':price,'reason':reason,'pnl_usd':pnl,'exchange':live['exchange']})
        else:
            events.append({'trade_id':trade['id'],'symbol':trade['symbol'],'price':price,'reason':'OPEN','exchange':live['exchange']})
    return events
