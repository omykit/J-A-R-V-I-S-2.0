from memory_service.database import _strip_libpq_only_params


def test_strips_sslmode_and_channel_binding():
    # Regression test: these are libpq-only params. SQLAlchemy's asyncpg
    # dialect forwards every URL query param straight to asyncpg.connect(),
    # which crashes with "unexpected keyword argument 'sslmode'" if they're
    # left in the URL (see database.py for the full explanation).
    url = (
        "postgresql+asyncpg://user:pw@ep-example.neon.tech/jarvis"
        "?sslmode=require&channel_binding=require"
    )
    result = _strip_libpq_only_params(url)
    assert "sslmode" not in result
    assert "channel_binding" not in result
    assert result.startswith("postgresql+asyncpg://user:pw@ep-example.neon.tech/jarvis")


def test_preserves_other_query_params():
    url = "postgresql+asyncpg://user:pw@host/db?sslmode=require&application_name=jarvis"
    result = _strip_libpq_only_params(url)
    assert "application_name=jarvis" in result
    assert "sslmode" not in result


def test_leaves_url_without_query_params_unchanged():
    url = "postgresql+asyncpg://user:pw@host/db"
    assert _strip_libpq_only_params(url) == url
