from __future__ import annotations

import asyncio

from app.audit import record_event
from app.config import settings
from app.monitor import monitor_open_trades
from app.orchestrator import MasterAgent
from app.storage import save_scan


async def run_cycle(master: MasterAgent | None = None, limit: int = 30):
    """Run one real-data scan and monitor cycle; no synthetic market observations."""
    agent = master or MasterAgent()
    results = await agent.scan(limit)
    save_scan(results)
    monitor_events = await monitor_open_trades()
    record_event(
        'scheduler_cycle',
        None,
        {
            'scan_count': len(results),
            'monitor_count': len(monitor_events),
            'mode': settings.trading_mode,
        },
    )
    return {'scans': results, 'monitor': monitor_events}


async def run_forever(interval_seconds: int = 60, limit: int = 30):
    """Continuously scan and monitor using live providers only."""
    if interval_seconds < 5:
        raise ValueError('interval_seconds must be at least 5')
    master = MasterAgent()
    while True:
        try:
            await run_cycle(master, limit)
        except Exception as exc:
            record_event('scheduler_error', None, {'error': str(exc)})
        await asyncio.sleep(interval_seconds)
