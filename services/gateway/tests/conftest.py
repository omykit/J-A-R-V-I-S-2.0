import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from httpx import ASGITransport, AsyncClient

from gateway.main import app


@pytest.fixture
async def client():
    # ASGITransport does not run lifespan events, so the background reminder
    # poller stays stopped here. reminders.check_once() is tested directly.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
