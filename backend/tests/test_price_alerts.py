import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.retailer import Retailer


async def _seed_retailer(db_session: AsyncSession, slug: str) -> Retailer:
    retailer = Retailer(name="楽天市場(テスト用)", slug=slug, base_url="https://www.rakuten.co.jp")
    db_session.add(retailer)
    await db_session.flush()
    return retailer


async def _register_login_and_create_product(
    client: AsyncClient, db_session: AsyncSession, email: str, slug: str
) -> tuple[int, str]:
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
async def test_create_and_list_price_alerts(client: AsyncClient, db_session: AsyncSession) -> None:
    product_id, token = await _register_login_and_create_product(
        client, db_session, "alert-owner@example.com", "rakuten-alert-1"
    )
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        f"/api/tracked-products/{product_id}/alerts",
        json={"rule_type": "price_below", "threshold_value": "1000.00"},
        headers=headers,
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["rule_type"] == "price_below"
    assert body["is_active"] is True

    list_response = await client.get(
        f"/api/tracked-products/{product_id}/alerts", headers=headers
    )
    assert len(list_response.json()) == 1


@pytest.mark.asyncio
async def test_update_and_delete_price_alert(client: AsyncClient, db_session: AsyncSession) -> None:
    product_id, token = await _register_login_and_create_product(
        client, db_session, "alert-owner2@example.com", "rakuten-alert-2"
    )
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        f"/api/tracked-products/{product_id}/alerts",
        json={"rule_type": "price_below", "threshold_value": "1000.00"},
        headers=headers,
    )
    alert_id = create_response.json()["id"]

    update_response = await client.patch(
        f"/api/tracked-products/{product_id}/alerts/{alert_id}",
        json={"is_active": False},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["is_active"] is False

    delete_response = await client.delete(
        f"/api/tracked-products/{product_id}/alerts/{alert_id}", headers=headers
    )
    assert delete_response.status_code == 204

    list_response = await client.get(
        f"/api/tracked-products/{product_id}/alerts", headers=headers
    )
    assert list_response.json() == []


@pytest.mark.asyncio
async def test_alerts_are_scoped_to_owner(client: AsyncClient, db_session: AsyncSession) -> None:
    product_id, token_a = await _register_login_and_create_product(
        client, db_session, "alert-usera@example.com", "rakuten-alert-3"
    )
    await client.post(
        "/api/auth/register",
        json={"email": "alert-userb@example.com", "password": "password123"},
    )
    login_b = await client.post(
        "/api/auth/login",
        data={"username": "alert-userb@example.com", "password": "password123"},
    )
    token_b = login_b.json()["access_token"]

    create_response = await client.post(
        f"/api/tracked-products/{product_id}/alerts",
        json={"rule_type": "price_below", "threshold_value": "1000.00"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    alert_id = create_response.json()["id"]

    get_as_b = await client.get(
        f"/api/tracked-products/{product_id}/alerts",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert get_as_b.status_code == 404

    delete_as_b = await client.delete(
        f"/api/tracked-products/{product_id}/alerts/{alert_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert delete_as_b.status_code == 404
