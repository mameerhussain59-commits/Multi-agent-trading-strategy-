from __future__ import annotations

from collections import defaultdict


def _asset_bucket(symbol: str) -> str:
    s = symbol.upper()
    if s in {'BTC', 'WBTC'}:
        return 'BTC'
    if s in {'ETH', 'WETH', 'STETH', 'WSTETH'}:
        return 'ETH'
    if s in {'SOL', 'JUP', 'RAY', 'JTO', 'PYTH'}:
        return 'SOL_ECOSYSTEM'
    if s in {'BNB', 'CAKE', 'XVS'}:
        return 'BNB_ECOSYSTEM'
    if s in {'LINK', 'UNI', 'AAVE', 'MKR', 'CRV', 'COMP'}:
        return 'DEFI'
    return s


def exposure_summary(open_trades: list[dict], account_equity: float) -> dict:
    by_bucket = defaultdict(float)
    total_notional = 0.0
    for trade in open_trades:
        payload = trade.get('payload', {})
        symbol = trade.get('symbol', '')
        try:
            qty = float(payload.get('remaining_size', payload.get('position_size', 0)))
            entry = float(payload.get('entry', 0))
        except (TypeError, ValueError):
            continue
        notional = max(0.0, qty * entry)
        by_bucket[_asset_bucket(symbol)] += notional
        total_notional += notional
    return {
        'total_notional_usd': total_notional,
        'total_notional_pct': (total_notional / account_equity * 100.0) if account_equity else 0.0,
        'buckets': dict(by_bucket),
    }


def exposure_gate(plan, open_trades: list[dict], account_equity: float, max_total_notional_pct: float = 50.0, max_bucket_pct: float = 25.0) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    summary = exposure_summary(open_trades, account_equity)
    try:
        proposed = float(plan.position_size) * float(plan.entry)
    except (TypeError, ValueError):
        return False, ['Invalid proposed position notional']

    max_total = account_equity * max_total_notional_pct / 100.0
    if summary['total_notional_usd'] + proposed > max_total:
        warnings.append(f'Total portfolio notional would exceed ${max_total:.2f}')

    bucket = _asset_bucket(plan.symbol)
    bucket_existing = float(summary['buckets'].get(bucket, 0.0))
    max_bucket = account_equity * max_bucket_pct / 100.0
    if bucket_existing + proposed > max_bucket:
        warnings.append(f'Exposure bucket {bucket} would exceed ${max_bucket:.2f}')

    return not warnings, warnings
