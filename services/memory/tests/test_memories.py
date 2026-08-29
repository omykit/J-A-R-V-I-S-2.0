async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_memory_upsert_and_list(client):
    response = await client.post("/memories", json={"key": "name", "value": "Omair"})
    assert response.status_code == 201
    assert response.json()["value"] == "Omair"

    response = await client.get("/memories/name")
    assert response.status_code == 200
    assert response.json()["value"] == "Omair"

    response = await client.get("/memories")
    assert response.status_code == 200
    keys = [entry["key"] for entry in response.json()]
    assert "name" in keys


async def test_memory_not_found(client):
    response = await client.get("/memories/does-not-exist")
    assert response.status_code == 404


async def test_health_reports_unavailable_when_database_is_down(client, monkeypatch):
    """Regression test: /health used to return a static "ok" without touching
    the database, so the container reported healthy while Neon was down."""
    from memory_service import main

    async def broken_session():
        class _Session:
            async def execute(self, *args, **kwargs):
                raise RuntimeError("connection refused")

        yield _Session()

    main.app.dependency_overrides[main.get_session] = broken_session
    try:
        response = await client.get("/health")
    finally:
        main.app.dependency_overrides.pop(main.get_session, None)

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert "connection refused" in body["detail"]
