import pytest

from app.scheduler import run_forever


@pytest.mark.asyncio
async def test_scheduler_rejects_too_short_interval():
    with pytest.raises(ValueError, match='at least 5'):
        await run_forever(interval_seconds=1)
