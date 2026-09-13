from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=settings.environment == "development")
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI の Depends() で使うセッション取得用ジェネレータ。"""
    async with async_session_factory() as session:
        yield session


# Celeryタスク専用のエンジン。FastAPIは1つのイベントループを起動時から使い続けるため
# コネクションプールが有効だが、Celeryタスクは1タスクごとに `asyncio.run()` で新しい
# イベントループを作るため、プールされた接続を使い回すと
# 「attached to a different loop」エラーになる。NullPoolで都度新規接続にして回避する。
celery_engine = create_async_engine(settings.database_url, poolclass=NullPool)
celery_session_factory = async_sessionmaker(celery_engine, expire_on_commit=False)
