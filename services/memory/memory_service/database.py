"""Database engine and session factory."""
from __future__ import annotations

import ssl
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings

# asyncpg's connect() takes SSL config via a connect_args `ssl` value (bool or
# ssl.SSLContext) — it has no `sslmode`/`channel_binding` kwargs (those are
# libpq/psycopg conventions). SQLAlchemy's asyncpg dialect forwards every URL
# query param straight through as a connect() kwarg, so a Neon connection
# string pasted with `?sslmode=require&channel_binding=require` (Neon's
# console includes these by default) crashes with
# "connect() got an unexpected keyword argument 'sslmode'". Strip them here
# and configure TLS explicitly instead.
_LIBPQ_ONLY_PARAMS = {"sslmode", "channel_binding"}


def _strip_libpq_only_params(url: str) -> str:
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k not in _LIBPQ_ONLY_PARAMS]
    return urlunsplit(parts._replace(query=urlencode(query)))


_connect_args = {"ssl": ssl.create_default_context()} if settings.db_ssl else {}

engine = create_async_engine(
    _strip_libpq_only_params(settings.database_url),
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
