import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.models.base import Base


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return Settings(
        telegram_bot_token="test-token",
        anthropic_api_key="test-key",
        openai_api_key="test-key",
        database_url="sqlite+aiosqlite:///test.db",
        default_currency="UYU",
    )


@pytest.fixture(scope="session")
async def engine(test_settings: Settings):
    eng = create_async_engine(test_settings.database_url, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()
