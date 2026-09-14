from __future__ import annotations
from datetime import datetime, time, timezone
from math import sqrt

from app.config import settings
from app.storage import open_paper_trades, realized_pnl_since


def _utc_day_start() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)


def _correlation(a: list[float], b: list[float]) -> float | None:
    n = min(len(a), len(b))
    if n < 20:
        return None
    x = [float(v) for v in a[-n:]]
    y = [float(v) for v in b[-n:]]
    mx, my = sum(x) / n, sum(y) / n
    cov = sum((u - mx) * (v - my) for u, v in zip(x, y))
    vx = sum((u - mx) ** 2 for u in x)
    vy = sum((v - my) ** 2 for v in y)
    if vx <= 0 or vy <= 0:
        return None
    return cov / sqrt(vx * vy)


def portfolio_gate(plan) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    open_trades = open_paper_trades()

    if any(t['symbol'].upper() == plan.symbol.upper() for t in open_trades):
        return False, ['An open paper position already exists for this symbol']

    realized_today = realized_pnl_since(_utc_day_start())
    max_daily_loss = settings.account_equity_usd * (settings.max_daily_loss_pct / 100.0)
    if realized_today <= -max_daily_loss:
        return False, [f'Daily loss kill switch active: realized PnL ${realized_today:.2f} exceeds loss limit ${max_daily_loss:.2f}']

    if len(open_trades) >= settings.max_concurrent_positions:
        warnings.append(f'Maximum concurrent positions reached ({settings.max_concurrent_positions})')

    total_risk = 0.0
    total_exposure = 0.0
    for trade in open_trades:
        payload = trade.get('payload', {})
        try:
            total_risk += float(payload.get('risk_usd', 0))
            total_exposure += float(payload.get('position_size', 0)) * float(payload.get('entry', 0))
        except (TypeError, ValueError):
            continue
        corr = _correlation(getattr(plan, 'market_returns', []), payload.get('market_returns', []))
        if corr is not None and abs(corr) >= settings.max_correlation:
            warnings.append(f'Correlation {corr:.2f} with open {trade["symbol"]} exceeds limit {settings.max_correlation:.2f}')

    proposed_total = total_risk + float(plan.risk_usd)
    max_total_risk = settings.account_equity_usd * (settings.max_total_risk_pct / 100.0)
    if proposed_total > max_total_risk:
        warnings.append(f'Total open+proposed risk ${proposed_total:.2f} exceeds portfolio cap ${max_total_risk:.2f}')

    proposed_exposure = total_exposure + float(plan.position_size) * float(plan.entry)
    max_exposure = settings.account_equity_usd * (settings.max_total_exposure_pct / 100.0)
    if proposed_exposure > max_exposure:
        warnings.append(f'Total exposure ${proposed_exposure:.2f} exceeds portfolio exposure cap ${max_exposure:.2f}')

    return not warnings, warnings
