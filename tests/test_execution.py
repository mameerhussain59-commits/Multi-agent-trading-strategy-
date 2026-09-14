import pytest

from app import execution


def test_live_execution_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(execution.settings, 'live_trading_enabled', False)
    monkeypatch.setattr(execution.settings, 'dry_run', True)
    monkeypatch.setattr(execution.settings, 'trading_mode', 'paper')
    monkeypatch.setattr(execution.settings, 'binance_api_key', 'test-key')
    monkeypatch.setattr(execution.settings, 'binance_api_secret', 'test-secret')

    executor = execution.BinanceExecutor()
    with pytest.raises(execution.ExecutionDisabled, match='disabled by safety configuration'):
        executor._signed({'symbol': 'BTCUSDT'})


def test_live_execution_requires_credentials(monkeypatch):
    monkeypatch.setattr(execution.settings, 'live_trading_enabled', True)
    monkeypatch.setattr(execution.settings, 'dry_run', False)
    monkeypatch.setattr(execution.settings, 'trading_mode', 'live')
    monkeypatch.setattr(execution.settings, 'binance_api_key', None)
    monkeypatch.setattr(execution.settings, 'binance_api_secret', None)

    executor = execution.BinanceExecutor()
    with pytest.raises(execution.ExecutionDisabled, match='credentials are missing'):
        executor._signed({'symbol': 'BTCUSDT'})
