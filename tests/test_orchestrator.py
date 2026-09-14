from types import SimpleNamespace

import pytest

from app import orchestrator


@pytest.mark.asyncio
async def test_master_scan_fails_closed_without_order_book(monkeypatch):
    token = SimpleNamespace(symbol='BTC', source_score=8.0)
    live = {
        'pair': 'BTCUSDT',
        'price': 100.0,
        'change_24h': 1.0,
        'volume_24h': 1000000.0,
        'high_24h': 101.0,
        'low_24h': 99.0,
        'exchange': 'bybit',
        'candles': [[i, 100.0, 101.0, 99.0, 100.0] for i in range(100)],
        'order_book': None,
        'observed_at': '2026-09-14T00:00:00+00:00',
    }

    async def fake_hunter(limit=30):
        return [token]

    async def fake_market(symbol):
        return live

    async def fake_cg(symbol):
        return {'market_cap': 1000000.0}

    async def fake_dex(symbol):
        return {'liquidity': {'usd': 500000.0}}

    monkeypatch.setattr(orchestrator.mrnasdog_scored_tokens, '__call__', fake_hunter, raising=False)
    monkeypatch.setattr(orchestrator, 'live_market', fake_market)
    monkeypatch.setattr(orchestrator, 'coingecko_coin', fake_cg)
    monkeypatch.setattr(orchestrator, 'dexscreener_token', fake_dex)
    monkeypatch.setattr(orchestrator, 'portfolio_gate', lambda plan: (True, []))
    monkeypatch.setattr(
        orchestrator,
        'technical_analysis',
        lambda *args, **kwargs: SimpleNamespace(timeframe='1h', trend='bullish', momentum_score=80.0, atr=1.0, rsi=60.0),
    )

    agent = orchestrator.MasterAgent()
    agent.hunter.run = fake_hunter
    results = await agent.scan(1)

    assert len(results) == 1
    assert results[0].trade.executable is False
    assert any('spread unavailable' in warning for warning in results[0].trade.warnings)
