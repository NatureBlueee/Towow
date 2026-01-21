"""Database connection configuration."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pydantic_settings import BaseSettings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    url: str = "postgresql+asyncpg://towow:password@localhost:5432/towow"

    class Config:
        env_prefix = "DATABASE_"


db_settings = DatabaseSettings()


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class Database:
    """Database connection manager with async support."""

    def __init__(self, database_url: str):
        """Initialize database connection.

        Args:
            database_url: Database connection URL.
        """
        # Convert standard postgresql:// to async driver URL
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://", "postgresql+asyncpg://"
            )

        self.engine: AsyncEngine = create_async_engine(
            database_url,
            echo=False,
            pool_size=10,
            max_overflow=20
        )
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session with automatic commit/rollback.

        Yields:
            AsyncSession: Database session.
        """
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def create_tables(self) -> None:
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def close(self) -> None:
        """Close database connection."""
        await self.engine.dispose()


# Global database instance (lazy initialization)
_db: Optional[Database] = None


def get_database() -> Database:
    """Get or create the global database instance."""
    global _db
    if _db is None:
        _db = Database(db_settings.url)
    return _db


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session.

    Yields:
        AsyncSession: Database session.
    """
    db = get_database()
    async with db.session() as session:
        yield session
