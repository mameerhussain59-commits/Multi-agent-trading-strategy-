from types import SimpleNamespace

import pytest

from app import backtest


@pytest.mark.asyncio
async def test_backtest_closes_open_trade_at_end_of_real_data(monkeypatch):
    rows = []
    for i in range(105):
        price = 100.0 + i
        rows.append([i, price, price + 2, price - 2, price + 1, 1000.0])

    monkeypatch.setattr(backtest, 'binance_klines', lambda *args, **kwargs: _rows(rows))
    monkeypatch.setattr(
        backtest,
        'technical_analysis',
        lambda *args, **kwargs: SimpleNamespace(trend='bullish', rsi=60.0, atr=1.0),
    )

    result = await backtest.backtest_binance('BTC', limit=105, initial_equity=10000.0, risk_pct=0.5)

    assert result['candles'] == 105
    assert result['data_source'] == 'Binance historical klines'
    assert result['trades'] >= 1
    assert any(trade['reason'] == 'END_OF_DATA' for trade in result.get('trade_log', [])) is False
    assert 'max_drawdown_pct' in result


async def _rows(rows):
    return rows
