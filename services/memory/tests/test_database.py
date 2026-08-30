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


def test_normalizes_neon_console_url_without_driver_suffix():
    """Neon's console emits "postgresql://..." with no driver. asyncpg is the
    only installed driver, so without this the engine picks psycopg2 and dies
    with ModuleNotFoundError deep inside SQLAlchemy."""
    from memory_service.database import _normalize_driver

    result = _normalize_driver("postgresql://u:p@ep-example.neon.tech/db")
    assert result.startswith("postgresql+asyncpg://")
    assert result == "postgresql+asyncpg://u:p@ep-example.neon.tech/db"


def test_normalizes_legacy_postgres_scheme():
    from memory_service.database import _normalize_driver

    assert _normalize_driver("postgres://u:p@host/db").startswith("postgresql+asyncpg://")


def test_leaves_correct_driver_untouched():
    from memory_service.database import _normalize_driver

    url = "postgresql+asyncpg://u:p@host/db"
    assert _normalize_driver(url) == url


def test_normalization_warns_so_a_repasted_url_is_visible(caplog):
    from memory_service.database import _normalize_driver

    with caplog.at_level("WARNING"):
        _normalize_driver("postgresql://u:p@host/db")
    assert "asyncpg" in caplog.text


def test_normalization_composes_with_libpq_stripping():
    """A raw Neon paste has BOTH problems at once."""
    from memory_service.database import _normalize_driver, _strip_libpq_only_params

    raw = "postgresql://u:p@ep-example.neon.tech/db?sslmode=require&channel_binding=require"
    result = _strip_libpq_only_params(_normalize_driver(raw))
    assert result.startswith("postgresql+asyncpg://")
    assert "sslmode" not in result and "channel_binding" not in result
