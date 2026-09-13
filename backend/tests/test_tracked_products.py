import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.retailer import Retailer


async def _seed_retailer(db_session: AsyncSession, slug: str) -> Retailer:
    """テスト用の小売店データを作る。本番シード('rakuten')と衝突しないよう一意なslugを使う。"""
    retailer = Retailer(name="楽天市場(テスト用)", slug=slug, base_url="https://www.rakuten.co.jp")
    db_session.add(retailer)
    await db_session.flush()
    return retailer


async def _register_and_login(
    client: AsyncClient, email: str, password: str = "password123"
) -> str:
    await client.post("/api/auth/register", json={"email": email, "password": password})
    login_response = await client.post(
        "/api/auth/login", data={"username": email, "password": password}
    )
    return login_response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_and_list_tracked_products(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    retailer = await _seed_retailer(db_session, "rakuten-test-1")
    token = await _register_and_login(client, "owner@example.com")

    create_response = await client.post(
        "/api/tracked-products",
        json={
            "retailer_id": retailer.id,
            "external_product_id": "item-001",
            "name": "テスト商品A",
            "product_url": "https://www.rakuten.co.jp/shop/item-001",
        },
        headers=_auth_headers(token),
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "テスト商品A"
    assert created["is_active"] is True

    list_response = await client.get("/api/tracked-products", headers=_auth_headers(token))
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


@pytest.mark.asyncio
async def test_create_with_unknown_retailer_is_rejected(client: AsyncClient) -> None:
    token = await _register_and_login(client, "owner2@example.com")

    response = await client.post(
        "/api/tracked-products",
        json={
            "retailer_id": 999999,
            "external_product_id": "item-001",
            "name": "テスト商品",
            "product_url": "https://example.com",
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_users_cannot_see_or_modify_others_products(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    retailer = await _seed_retailer(db_session, "rakuten-test-2")
    token_a = await _register_and_login(client, "usera@example.com")
    token_b = await _register_and_login(client, "userb@example.com")

    create_response = await client.post(
        "/api/tracked-products",
        json={
            "retailer_id": retailer.id,
            "external_product_id": "item-002",
            "name": "ユーザーAの商品",
            "product_url": "https://www.rakuten.co.jp/shop/item-002",
        },
        headers=_auth_headers(token_a),
    )
    product_id = create_response.json()["id"]

    get_as_b = await client.get(
        f"/api/tracked-products/{product_id}", headers=_auth_headers(token_b)
    )
    assert get_as_b.status_code == 404

    update_as_b = await client.patch(
        f"/api/tracked-products/{product_id}",
        json={"name": "改ざん"},
        headers=_auth_headers(token_b),
    )
    assert update_as_b.status_code == 404

    list_as_b = await client.get("/api/tracked-products", headers=_auth_headers(token_b))
    assert list_as_b.json() == []


@pytest.mark.asyncio
async def test_update_and_delete_tracked_product(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    retailer = await _seed_retailer(db_session, "rakuten-test-3")
    token = await _register_and_login(client, "owner3@example.com")

    create_response = await client.post(
        "/api/tracked-products",
        json={
            "retailer_id": retailer.id,
            "external_product_id": "item-003",
            "name": "更新前",
            "product_url": "https://www.rakuten.co.jp/shop/item-003",
        },
        headers=_auth_headers(token),
    )
    product_id = create_response.json()["id"]

    update_response = await client.patch(
        f"/api/tracked-products/{product_id}",
        json={"name": "更新後", "is_active": False},
        headers=_auth_headers(token),
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "更新後"
    assert update_response.json()["is_active"] is False

    delete_response = await client.delete(
        f"/api/tracked-products/{product_id}", headers=_auth_headers(token)
    )
    assert delete_response.status_code == 204

    get_response = await client.get(
        f"/api/tracked-products/{product_id}", headers=_auth_headers(token)
    )
    assert get_response.status_code == 404
