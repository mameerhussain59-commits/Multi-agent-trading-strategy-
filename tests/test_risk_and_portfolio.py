from types import SimpleNamespace

from app import portfolio, risk


def test_trade_plan_respects_risk_and_position_cap(monkeypatch):
    monkeypatch.setattr(risk.settings, 'account_equity_usd', 10000.0)
    monkeypatch.setattr(risk.settings, 'risk_per_trade_pct', 0.5)
    monkeypatch.setattr(risk.settings, 'max_position_pct', 10.0)
    monkeypatch.setattr(risk.settings, 'min_signal_score', 65.0)
    monkeypatch.setattr(risk.settings, 'trading_mode', 'paper')

    plan = risk.make_trade_plan('BTC', 100.0, 2.0, 80.0)
    assert plan.executable is True
    assert plan.risk_usd <= 50.0
    assert plan.position_size * plan.entry <= 1000.0
    assert plan.take_profit_1 > plan.entry
    assert plan.take_profit_2 > plan.take_profit_1
    assert plan.take_profit_3 > plan.take_profit_2


def test_portfolio_gate_blocks_duplicate(monkeypatch):
    monkeypatch.setattr(portfolio, 'open_paper_trades', lambda: [{'symbol': 'BTC', 'payload': {'risk_usd': 50}}])
    plan = SimpleNamespace(symbol='btc', risk_usd=50.0)
    allowed, warnings = portfolio.portfolio_gate(plan)
    assert allowed is False
    assert any('already exists' in warning for warning in warnings)


def test_portfolio_gate_blocks_total_risk(monkeypatch):
    monkeypatch.setattr(portfolio.settings, 'account_equity_usd', 10000.0)
    monkeypatch.setattr(portfolio.settings, 'max_total_risk_pct', 2.0)
    monkeypatch.setattr(portfolio.settings, 'max_concurrent_positions', 5)
    monkeypatch.setattr(
        portfolio,
        'open_paper_trades',
        lambda: [{'symbol': 'ETH', 'payload': {'risk_usd': 150.0}}],
    )
    plan = SimpleNamespace(symbol='SOL', risk_usd=100.0)
    allowed, warnings = portfolio.portfolio_gate(plan)
    assert allowed is False
    assert any('portfolio cap' in warning for warning in warnings)
