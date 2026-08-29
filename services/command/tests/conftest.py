import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from command_service.main import app, get_memory_client


class FakeMemoryService:
    """In-memory stand-in for memory-service.

    command-service only ever talks to memory-service over HTTP, so tests
    route those calls here instead of over the network. Records every call
    so tests can assert on the request contract, not just the response text.
    """

    def __init__(self) -> None:
        self.memories: dict[str, object] = {}
        self.reminders: list[dict] = []
        self.calls: list[tuple[str, str, dict | None]] = []
        self.fail_next = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        import json

        method = request.method
        path = request.url.path
        body = json.loads(request.content) if request.content else None
        self.calls.append((method, path, body))

        if self.fail_next:
            self.fail_next = False
            return httpx.Response(500, json={"detail": "boom"})

        if method == "GET" and path == "/memories":
            return httpx.Response(
                200,
                json=[{"key": key, "value": value} for key, value in self.memories.items()],
            )
        if method == "POST" and path == "/memories":
            self.memories[body["key"]] = body["value"]
            return httpx.Response(201, json=body)
        if method == "GET" and path == "/reminders":
            return httpx.Response(200, json=self.reminders)
        if method == "POST" and path == "/reminders":
            record = {"id": len(self.reminders) + 1, "triggered": False, **body}
            self.reminders.append(record)
            return httpx.Response(201, json=record)
        return httpx.Response(404, json={"detail": "not found"})


@pytest.fixture(autouse=True)
def stub_geolocation(monkeypatch):
    """Keep tests off the network.

    Time requests with no location fall back to IP geolocation, which would
    otherwise make a real HTTP call to ipapi.co on every such test.
    """
    from command_service import handler as handler_module

    monkeypatch.setattr(handler_module, "get_local_timezone", lambda: "Asia/Kuwait")


@pytest.fixture
def memory_service() -> FakeMemoryService:
    return FakeMemoryService()


@pytest.fixture
async def client(memory_service):
    async def override_get_memory_client():
        transport = httpx.MockTransport(memory_service.handler)
        async with httpx.AsyncClient(transport=transport, base_url="http://memory") as mc:
            yield mc

    app.dependency_overrides[get_memory_client] = override_get_memory_client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
