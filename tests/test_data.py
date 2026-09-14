import pytest

from app import data


@pytest.mark.asyncio
async def test_coingecko_market_lookup_uses_real_response_cache(monkeypatch):
    calls = []

    class FakeResponse:
        def json(self):
            return [{'symbol': 'btc', 'market_cap': 100.0}]

    async def fake_get(url, params=None, headers=None):
        calls.append((url, params))
        return FakeResponse()

    data._CG_CACHE = None
    monkeypatch.setattr(data.http, 'get', fake_get)

    assert (await data.coingecko_coin('BTC'))['symbol'] == 'btc'
    assert (await data.coingecko_coin('BTC'))['symbol'] == 'btc'
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_bybit_order_book_rejects_provider_error(monkeypatch):
    class FakeResponse:
        def json(self):
            return {'retCode': 10001, 'retMsg': 'bad symbol'}

    async def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(data.http, 'get', fake_get)
    with pytest.raises(data.DataError, match='bad symbol'):
        await data.bybit_order_book('BADUSDT')
