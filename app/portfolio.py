from __future__ import annotations

from app.config import settings
from app.storage import open_paper_trades


def portfolio_gate(plan) -> tuple[bool, list[str]]:
    """Apply portfolio-level guardrails to a proposed paper trade."""
    warnings: list[str] = []
    open_trades = open_paper_trades()

    if any(t['symbol'].upper() == plan.symbol.upper() for t in open_trades):
        return False, ['An open paper position already exists for this symbol']

    if len(open_trades) >= settings.max_concurrent_positions:
        warnings.append(f'Maximum concurrent positions reached ({settings.max_concurrent_positions})')

    total_risk = 0.0
    for trade in open_trades:
        try:
            total_risk += float(trade.get('payload', {}).get('risk_usd', 0))
        except (TypeError, ValueError):
            continue

    proposed_total = total_risk + float(plan.risk_usd)
    max_total_risk = settings.account_equity_usd * (settings.max_total_risk_pct / 100.0)
    if proposed_total > max_total_risk:
        warnings.append(
            f'Total open+proposed risk ${proposed_total:.2f} exceeds portfolio cap ${max_total_risk:.2f}'
        )

    return not warnings, warnings
