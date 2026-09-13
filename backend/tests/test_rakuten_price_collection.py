import httpx
import pytest
import respx
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.retailer import Retailer
from app.services.rakuten import ITEM_SEARCH_URL


async def _seed_retailer(db_session: AsyncSession, slug: str) -> Retailer:
    retailer = Retailer(name="楽天市場(テスト用)", slug=slug, base_url="https://www.rakuten.co.jp")
    db_session.add(retailer)
    await db_session.flush()
    return retailer


async def _register_login_and_create_product(
    client: AsyncClient, db_session: AsyncSession, email: str, slug: str
) -> int:
    retailer = await _seed_retailer(db_session, slug)
    await client.post("/api/auth/register", json={"email": email, "password": "password123"})
    login_response = await client.post(
        "/api/auth/login", data={"username": email, "password": "password123"}
    )
    token = login_response.json()["access_token"]

    create_response = await client.post(
        "/api/tracked-products",
        json={
            "retailer_id": retailer.id,
            "external_product_id": "item-code-abc",
            "name": "監視商品",
            "product_url": "https://www.rakuten.co.jp/shop/item-code-abc",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return create_response.json()["id"], token


@pytest.mark.asyncio
@respx.mock
async def test_collect_price_creates_snapshot_from_rakuten_response(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "rakuten_app_id", "test-app-id")
    monkeypatch.setattr(settings, "rakuten_access_key", "test-access-key")

    product_id, token = await _register_login_and_create_product(
        client, db_session, "collector@example.com", "rakuten-collect-1"
    )

    respx.get(ITEM_SEARCH_URL).mock(
        return_value=httpx.Response(200, json={"Items": [{"itemPrice": 2980}]})
    )

    response = await client.post(
        f"/api/tracked-products/{product_id}/collect-price",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["price"] == "2980.00"
    assert body["tracked_product_id"] == product_id

    history_response = await client.get(
        f"/api/tracked-products/{product_id}/price-snapshots",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(history_response.json()) == 1


@pytest.mark.asyncio
@respx.mock
async def test_collect_price_returns_502_when_rakuten_item_not_found(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "rakuten_app_id", "test-app-id")
    monkeypatch.setattr(settings, "rakuten_access_key", "test-access-key")

    product_id, token = await _register_login_and_create_product(
        client, db_session, "collector2@example.com", "rakuten-collect-2"
    )

    respx.get(ITEM_SEARCH_URL).mock(return_value=httpx.Response(200, json={"Items": []}))

    response = await client.post(
        f"/api/tracked-products/{product_id}/collect-price",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 502


@pytest.mark.asyncio
async def test_collect_price_fails_clearly_without_app_id(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "rakuten_app_id", "")

    product_id, token = await _register_login_and_create_product(
        client, db_session, "collector3@example.com", "rakuten-collect-3"
    )

    response = await client.post(
        f"/api/tracked-products/{product_id}/collect-price",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 502
    assert "RAKUTEN_APP_ID" in response.json()["detail"]
