import pytest
from app import scheduler


@pytest.mark.asyncio
async def test_run_cycle_persists_scan_and_audits(monkeypatch):
    class FakeMaster:
        async def scan(self, limit):
            return ["real-result"]

    saved = []
    events = []

    async def fake_monitor():
        return [{"symbol": "BTC", "reason": "NONE"}]

    monkeypatch.setattr(scheduler, "save_scan", lambda results: saved.append(results))
    monkeypatch.setattr(scheduler, "monitor_open_trades", fake_monitor)
    monkeypatch.setattr(scheduler, "record_event", lambda *args: events.append(args))

    result = await scheduler.run_cycle(FakeMaster(), limit=7)

    assert result["scans"] == ["real-result"]
    assert result["monitor"] == [{"symbol": "BTC", "reason": "NONE"}]
    assert saved == [["real-result"]]
    assert events[0][0] == "scheduler_cycle"
    assert events[0][2]["scan_count"] == 1
    assert events[0][2]["monitor_count"] == 1


@pytest.mark.asyncio
async def test_run_forever_audits_cycle_errors(monkeypatch):
    calls = []
    errors = []

    async def fake_cycle(master, limit):
        calls.append((master, limit))
        raise RuntimeError("provider unavailable")

    async def fake_sleep(seconds):
        raise RuntimeError("stop-test-loop")

    monkeypatch.setattr(scheduler, "run_cycle", fake_cycle)
    monkeypatch.setattr(scheduler, "record_event", lambda *args: errors.append(args))
    monkeypatch.setattr(scheduler.asyncio, "sleep", fake_sleep)

    with pytest.raises(RuntimeError, match="stop-test-loop"):
        await scheduler.run_forever(interval_seconds=5, limit=9)

    assert len(calls) == 1
    assert errors[0][0] == "scheduler_error"
    assert errors[0][2]["error"] == "provider unavailable"
