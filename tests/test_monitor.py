from types import SimpleNamespace

import pytest

from app import monitor


@pytest.mark.asyncio
async def test_monitor_partial_take_profits(monkeypatch):
    trade = {
        'id': 7,
        'symbol': 'BTC',
        'payload': {
            'entry': 100.0,
            'stop_loss': 90.0,
            'take_profit_1': 110.0,
            'take_profit_2': 120.0,
            'take_profit_3': 130.0,
            'position_size': 9.0,
            'remaining_size': 9.0,
            'tp1_hit': False,
            'tp2_hit': False,
            'breakeven_armed': False,
        },
    }
    monkeypatch.setattr(monitor, 'open_paper_trades', lambda: [trade])
    monkeypatch.setattr(monitor, 'live_market', lambda symbol: _live(110.0))
    closed = []
    monkeypatch.setattr(monitor, 'close_paper_trade', lambda trade_id, price, reason, quantity=None: closed.append((trade_id, price, reason, quantity)) or 6.0)
    updated = []
    monkeypatch.setattr(monitor, 'update_paper_trade_payload', lambda trade_id, payload: updated.append((trade_id, payload.copy())))

    events = await monitor.monitor_open_trades()

    assert closed == [(7, 110.0, 'TAKE_PROFIT_1', 3.0)]
    assert updated[-1][1]['remaining_size'] == 6.0
    assert updated[-1][1]['tp1_hit'] is True
    assert updated[-1][1]['breakeven_armed'] is True
    assert updated[-1][1]['stop_loss'] == 100.0
    assert events[0]['reason'] == 'TAKE_PROFIT_1_PARTIAL'


def _live(price):
    return {'price': price, 'exchange': 'test-real-provider'}
