"""Database connectivity, engine initialization, and session dependency providers."""

from collections.abc import AsyncGenerator, Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""

    pass


def get_async_database_url(url: str) -> str:
    """Normalize a database URL to use an asynchronous driver."""
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def get_sync_database_url(url: str) -> str:
    """Normalize a database URL to use a synchronous driver."""
    if url.startswith("sqlite+aiosqlite:///"):
        return url.replace("sqlite+aiosqlite:///", "sqlite:///", 1)
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    return url


async_db_url: str = get_async_database_url(settings.DATABASE_URL)
sync_db_url: str = get_sync_database_url(settings.DATABASE_URL)

async_engine_args: dict[str, dict[str, bool]] = {}
sync_engine_args: dict[str, dict[str, bool]] = {}

if "sqlite" in async_db_url:
    async_engine_args["connect_args"] = {"check_same_thread": False}
    sync_engine_args["connect_args"] = {"check_same_thread": False}

# Asynchronous engine & session factory
async_engine: AsyncEngine = create_async_engine(
    async_db_url,
    echo=settings.DEBUG,
    **async_engine_args,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Synchronous engine & session factory (used for tooling/scripts)
engine = create_engine(
    sync_db_url,
    echo=settings.DEBUG,
    **sync_engine_args,
)

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an asynchronous database session."""
    async with AsyncSessionLocal() as session:
        yield session


def get_sync_db() -> Generator[Session, None, None]:
    """FastAPI or CLI dependency yielding a synchronous database session."""
    with SessionLocal() as session:
        yield session
