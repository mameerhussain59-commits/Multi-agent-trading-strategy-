from __future__ import annotations

from app.data import live_market
from app.storage import open_paper_trades, close_paper_trade, update_paper_trade_payload


async def monitor_open_trades():
    events = []
    for trade in open_paper_trades():
        try:
            live = await live_market(trade['symbol'])
            price = float(live['price'])
            plan = trade['payload']
            remaining = float(plan.get('remaining_size', plan['position_size']))
            original = float(plan['position_size'])

            if price <= float(plan['stop_loss']):
                pnl = close_paper_trade(trade['id'], price, 'STOP_LOSS')
                events.append({'trade_id': trade['id'], 'symbol': trade['symbol'], 'price': price, 'reason': 'STOP_LOSS', 'pnl_usd': pnl, 'exchange': live['exchange']})
                continue

            if price >= float(plan['take_profit_1']) and not plan.get('tp1_hit', False):
                qty = min(remaining, original / 3.0)
                pnl = close_paper_trade(trade['id'], price, 'TAKE_PROFIT_1', qty)
                remaining -= qty
                plan['remaining_size'] = remaining
                plan['tp1_hit'] = True
                plan['breakeven_armed'] = True
                plan['stop_loss'] = max(float(plan['stop_loss']), float(plan['entry']))
                update_paper_trade_payload(trade['id'], plan)
                events.append({'trade_id': trade['id'], 'symbol': trade['symbol'], 'price': price, 'reason': 'TAKE_PROFIT_1_PARTIAL', 'quantity': qty, 'pnl_usd': pnl, 'exchange': live['exchange']})

            if price >= float(plan['take_profit_2']) and not plan.get('tp2_hit', False):
                qty = min(remaining, original / 3.0)
                pnl = close_paper_trade(trade['id'], price, 'TAKE_PROFIT_2', qty)
                remaining -= qty
                plan['remaining_size'] = remaining
                plan['tp2_hit'] = True
                plan['breakeven_armed'] = True
                update_paper_trade_payload(trade['id'], plan)
                events.append({'trade_id': trade['id'], 'symbol': trade['symbol'], 'price': price, 'reason': 'TAKE_PROFIT_2_PARTIAL', 'quantity': qty, 'pnl_usd': pnl, 'exchange': live['exchange']})

            if remaining <= 1e-12:
                continue

            if price >= float(plan['take_profit_3']):
                pnl = close_paper_trade(trade['id'], price, 'TAKE_PROFIT_3')
                events.append({'trade_id': trade['id'], 'symbol': trade['symbol'], 'price': price, 'reason': 'TAKE_PROFIT_3', 'pnl_usd': pnl, 'exchange': live['exchange']})
            else:
                events.append({'trade_id': trade['id'], 'symbol': trade['symbol'], 'price': price, 'reason': 'OPEN', 'remaining_size': remaining, 'breakeven_armed': bool(plan.get('breakeven_armed', False)), 'exchange': live['exchange']})
        except Exception as exc:
            events.append({'trade_id': trade['id'], 'symbol': trade['symbol'], 'reason': 'MONITOR_ERROR', 'error': str(exc)})
    return events
