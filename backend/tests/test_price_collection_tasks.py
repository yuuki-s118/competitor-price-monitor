from contextlib import asynccontextmanager

import httpx
import pytest
import respx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.retailer import Retailer
from app.models.tracked_product import TrackedProduct
from app.models.user import User
from app.services.rakuten import ITEM_SEARCH_URL
from app.tasks.price_collection import _collect_price_for_product, _dispatch_all_active_products


@asynccontextmanager
async def _reuse_session(session: AsyncSession):
    """テスト用のセッション(ロールバックはfixture側に任せ、ここではcloseしない)。"""
    yield session


async def _seed_user_and_product(
    db_session: AsyncSession, slug: str, is_active: bool = True
) -> int:
    user = User(email=f"{slug}@example.com", hashed_password="x")
    retailer = Retailer(name="楽天市場(テスト用)", slug=slug, base_url="https://www.rakuten.co.jp")
    db_session.add_all([user, retailer])
    await db_session.flush()

    product = TrackedProduct(
        user_id=user.id,
        retailer_id=retailer.id,
        external_product_id="item-code-abc",
        name="監視商品",
        product_url="https://www.rakuten.co.jp/shop/item-code-abc",
        is_active=is_active,
    )
    db_session.add(product)
    await db_session.flush()
    return product.id


@pytest.mark.asyncio
@respx.mock
async def test_collect_price_for_product_saves_snapshot(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "rakuten_app_id", "test-app-id")
    monkeypatch.setattr(settings, "rakuten_access_key", "test-access-key")

    product_id = await _seed_user_and_product(db_session, "task-collect-1")
    respx.get(ITEM_SEARCH_URL).mock(
        return_value=httpx.Response(200, json={"Items": [{"itemPrice": 1500}]})
    )

    await _collect_price_for_product(
        product_id, session_factory=lambda: _reuse_session(db_session)
    )

    product = await db_session.get(TrackedProduct, product_id)
    await db_session.refresh(product, attribute_names=["price_snapshots"])
    assert len(product.price_snapshots) == 1
    assert product.price_snapshots[0].price == 1500


@pytest.mark.asyncio
async def test_collect_price_for_product_skips_inactive_product(db_session: AsyncSession) -> None:
    product_id = await _seed_user_and_product(db_session, "task-collect-2", is_active=False)

    # モックを張らずに実行し、実際にAPIへ問い合わせていない(＝スキップされた)ことを確認する
    await _collect_price_for_product(
        product_id, session_factory=lambda: _reuse_session(db_session)
    )

    product = await db_session.get(TrackedProduct, product_id)
    await db_session.refresh(product, attribute_names=["price_snapshots"])
    assert product.price_snapshots == []


@pytest.mark.asyncio
async def test_dispatch_all_active_products_only_queues_active_ones(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    active_id = await _seed_user_and_product(db_session, "task-dispatch-1", is_active=True)
    inactive_id = await _seed_user_and_product(db_session, "task-dispatch-2", is_active=False)

    dispatched: list[int] = []
    monkeypatch.setattr(
        "app.tasks.price_collection.collect_price_for_product.delay",
        lambda product_id: dispatched.append(product_id),
    )

    await _dispatch_all_active_products(session_factory=lambda: _reuse_session(db_session))

    assert active_id in dispatched
    assert inactive_id not in dispatched
