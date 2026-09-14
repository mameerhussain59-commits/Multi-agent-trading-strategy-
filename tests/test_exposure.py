from types import SimpleNamespace

from app.exposure import exposure_gate, exposure_summary


def test_exposure_summary_uses_remaining_position_size():
    trades = [{'symbol': 'BTC', 'payload': {'entry': 100.0, 'position_size': 5.0, 'remaining_size': 2.0}}]
    summary = exposure_summary(trades, 1000.0)
    assert summary['total_notional_usd'] == 200.0
    assert summary['buckets']['BTC'] == 200.0


def test_exposure_gate_blocks_bucket_concentration():
    trades = [{'symbol': 'BTC', 'payload': {'entry': 100.0, 'position_size': 2.0}}]
    plan = SimpleNamespace(symbol='BTC', entry=100.0, position_size=1.0)
    allowed, warnings = exposure_gate(plan, trades, 1000.0, max_total_notional_pct=100.0, max_bucket_pct=25.0)
    assert allowed is False
    assert any('Exposure bucket BTC' in warning for warning in warnings)
