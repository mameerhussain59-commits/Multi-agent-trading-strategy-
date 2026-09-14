from datetime import datetime, timedelta, timezone

from app import storage


def test_realized_pnl_uses_close_time(monkeypatch):
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    old_created = (start - timedelta(days=1)).isoformat()
    closed_at = (start + timedelta(minutes=1)).isoformat()

    class FakeContext:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def execute(self, query, params):
            assert 'COALESCE(closed_at, created_at)' in query
            class Row:
                def fetchone(self):
                    return (25.0,)
            return Row()

    monkeypatch.setattr(storage, '_connect', lambda: FakeContext())
    assert storage.realized_pnl_since(start) == 25.0
