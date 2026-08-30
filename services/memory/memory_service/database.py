"""Database engine and session factory."""
from __future__ import annotations

import logging
import ssl
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings

logger = logging.getLogger(__name__)

# asyncpg's connect() takes SSL config via a connect_args `ssl` value (bool or
# ssl.SSLContext) — it has no `sslmode`/`channel_binding` kwargs (those are
# libpq/psycopg conventions). SQLAlchemy's asyncpg dialect forwards every URL
# query param straight through as a connect() kwarg, so a Neon connection
# string pasted with `?sslmode=require&channel_binding=require` (Neon's
# console includes these by default) crashes with
# "connect() got an unexpected keyword argument 'sslmode'". Strip them here
# and configure TLS explicitly instead.
_LIBPQ_ONLY_PARAMS = {"sslmode", "channel_binding"}

# Neon's console hands out connection strings as "postgresql://..." with no
# driver suffix. asyncpg is the only driver in requirements.txt (psycopg2 is
# not installed and is not supported here), so a pasted Neon string fails deep
# inside SQLAlchemy with "ModuleNotFoundError: No module named 'psycopg2'" --
# an error that names neither the URL nor the real cause. Normalize instead,
# and warn so a re-pasted string is visible rather than silent.
_ASYNC_DRIVER = "postgresql+asyncpg://"


def _normalize_driver(url: str) -> str:
    if url.startswith("postgresql://"):
        logger.warning(
            "DATABASE_URL had no driver suffix; assuming asyncpg. "
            "Set the scheme to postgresql+asyncpg:// to silence this."
        )
        return _ASYNC_DRIVER + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        logger.warning(
            "DATABASE_URL used the legacy postgres:// scheme; assuming asyncpg."
        )
        return _ASYNC_DRIVER + url[len("postgres://"):]
    return url


def _strip_libpq_only_params(url: str) -> str:
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k not in _LIBPQ_ONLY_PARAMS]
    return urlunsplit(parts._replace(query=urlencode(query)))


_connect_args = {"ssl": ssl.create_default_context()} if settings.db_ssl else {}

engine = create_async_engine(
    _strip_libpq_only_params(_normalize_driver(settings.database_url)),
    echo=settings.echo_sql,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args=_connect_args,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        yield session
