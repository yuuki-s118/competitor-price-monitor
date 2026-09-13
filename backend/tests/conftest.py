import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.session import get_db
from app.main import app

# pytest-asyncio はテスト関数ごとに新しいイベントループを使うため、
# コネクションプールを持つと前のループに紐づいた接続を使い回して壊れる。
# NullPool で「毎回新規接続・使い回さない」テスト専用エンジンにする。
test_engine = create_async_engine(settings.database_url, poolclass=NullPool)


@pytest.fixture
async def db_session():
    """1テストごとにトランザクションを張り、終了時にロールバックする。

    アプリ側の `db.commit()` はセーブポイントの解放として扱われるため、
    実DBには何も残らない(同じメールアドレスで何度テストしても衝突しない)。
    """
    async with test_engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
