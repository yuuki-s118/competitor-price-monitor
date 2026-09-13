import httpx
import pytest
import respx
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.retailer import Retailer
from app.models.tracked_product import TrackedProduct
from app.models.user import User
from app.services.rakuten import ITEM_SEARCH_URL


async def _seed_product(db_session: AsyncSession, slug: str, is_active: bool = True) -> int:
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
async def test_collect_all_prices_rejects_missing_or_wrong_secret(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "internal_task_secret", "correct-secret")

    no_header = await client.post("/api/internal/collect-all-prices")
    assert no_header.status_code == 401

    wrong_header = await client.post(
        "/api/internal/collect-all-prices", headers={"X-Internal-Secret": "wrong"}
    )
    assert wrong_header.status_code == 401


@pytest.mark.asyncio
async def test_collect_all_prices_rejects_when_secret_not_configured(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "internal_task_secret", "")

    response = await client.post(
        "/api/internal/collect-all-prices", headers={"X-Internal-Secret": ""}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
@respx.mock
async def test_collect_all_prices_only_collects_active_products(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "internal_task_secret", "correct-secret")
    monkeypatch.setattr(settings, "rakuten_app_id", "test-app-id")
    monkeypatch.setattr(settings, "rakuten_access_key", "test-access-key")

    active_id = await _seed_product(db_session, "internal-collect-1", is_active=True)
    inactive_id = await _seed_product(db_session, "internal-collect-2", is_active=False)

    respx.get(ITEM_SEARCH_URL).mock(
        return_value=httpx.Response(200, json={"Items": [{"itemPrice": 1980}]})
    )

    response = await client.post(
        "/api/internal/collect-all-prices", headers={"X-Internal-Secret": "correct-secret"}
    )

    assert response.status_code == 200
    # 開発DBに残る他のアクティブ商品を含む可能性があるため、件数は下限のみ確認する
    assert response.json()["collected"] >= 1

    active_product = await db_session.get(TrackedProduct, active_id)
    await db_session.refresh(active_product, attribute_names=["price_snapshots"])
    assert len(active_product.price_snapshots) == 1

    inactive_product = await db_session.get(TrackedProduct, inactive_id)
    await db_session.refresh(inactive_product, attribute_names=["price_snapshots"])
    assert inactive_product.price_snapshots == []
