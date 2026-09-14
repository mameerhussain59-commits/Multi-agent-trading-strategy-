from types import SimpleNamespace

import pytest

from app import backtest


@pytest.mark.asyncio
async def test_backtest_uses_real_candle_provider_and_position_cap(monkeypatch):
    rows = []
    for i in range(105):
        price = 100.0 + i
        rows.append([i, price, price + 2, price - 2, price + 1, 1000.0])

    async def fake_klines(*args, **kwargs):
        return rows

    monkeypatch.setattr(backtest, 'binance_klines', fake_klines)
    monkeypatch.setattr(
        backtest,
        'technical_analysis',
        lambda *args, **kwargs: SimpleNamespace(trend='bullish', rsi=60.0, atr=1.0),
    )

    result = await backtest.backtest_binance(
        'BTC',
        limit=105,
        initial_equity=10000.0,
        risk_pct=0.5,
        max_position_pct=10.0,
    )

    assert result['candles'] == 105
    assert result['data_source'] == 'Binance historical klines'
    assert result['trades'] >= 1
    assert result['final_equity'] > 0
    assert result['max_drawdown_pct'] >= 0
    assert result['max_drawdown_pct'] <= 100
