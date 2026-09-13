import httpx
import pytest
import respx
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.retailer import Retailer
from app.services import price_alert_evaluation
from app.services.rakuten import ITEM_SEARCH_URL


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


def _mock_sent_emails(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    sent_to: list[str] = []

    async def fake_send_alert_email(to_email: str, subject: str, body: str) -> None:
        sent_to.append(to_email)

    monkeypatch.setattr(price_alert_evaluation, "send_alert_email", fake_send_alert_email)
    return sent_to


@pytest.mark.asyncio
@respx.mock
async def test_price_below_alert_sends_notification_on_first_trigger(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "rakuten_app_id", "test-app-id")
    monkeypatch.setattr(settings, "rakuten_access_key", "test-access-key")
    sent_to = _mock_sent_emails(monkeypatch)

    product_id, token = await _register_login_and_create_product(
        client, db_session, "notify1@example.com", "rakuten-notify-1"
    )
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        f"/api/tracked-products/{product_id}/alerts",
        json={"rule_type": "price_below", "threshold_value": "3000.00"},
        headers=headers,
    )

    respx.get(ITEM_SEARCH_URL).mock(
        return_value=httpx.Response(200, json={"Items": [{"itemPrice": 2500}]})
    )
    response = await client.post(
        f"/api/tracked-products/{product_id}/collect-price", headers=headers
    )
    assert response.status_code == 201
    assert sent_to == ["notify1@example.com"]

    logs_response = await client.get(
        f"/api/tracked-products/{product_id}/notification-logs", headers=headers
    )
    assert len(logs_response.json()) == 1


@pytest.mark.asyncio
@respx.mock
async def test_price_below_alert_does_not_renotify_while_still_below(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "rakuten_app_id", "test-app-id")
    monkeypatch.setattr(settings, "rakuten_access_key", "test-access-key")
    sent_to = _mock_sent_emails(monkeypatch)

    product_id, token = await _register_login_and_create_product(
        client, db_session, "notify2@example.com", "rakuten-notify-2"
    )
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        f"/api/tracked-products/{product_id}/alerts",
        json={"rule_type": "price_below", "threshold_value": "3000.00"},
        headers=headers,
    )

    respx.get(ITEM_SEARCH_URL).mock(
        return_value=httpx.Response(200, json={"Items": [{"itemPrice": 2500}]})
    )
    await client.post(f"/api/tracked-products/{product_id}/collect-price", headers=headers)
    await client.post(f"/api/tracked-products/{product_id}/collect-price", headers=headers)

    assert sent_to == ["notify2@example.com"]

    logs_response = await client.get(
        f"/api/tracked-products/{product_id}/notification-logs", headers=headers
    )
    assert len(logs_response.json()) == 1


@pytest.mark.asyncio
@respx.mock
async def test_price_drop_percent_alert_triggers_on_sufficient_drop(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "rakuten_app_id", "test-app-id")
    monkeypatch.setattr(settings, "rakuten_access_key", "test-access-key")
    sent_to = _mock_sent_emails(monkeypatch)

    product_id, token = await _register_login_and_create_product(
        client, db_session, "notify3@example.com", "rakuten-notify-3"
    )
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        f"/api/tracked-products/{product_id}/alerts",
        json={"rule_type": "price_drop_percent", "threshold_value": "10.00"},
        headers=headers,
    )

    route = respx.get(ITEM_SEARCH_URL)

    route.mock(return_value=httpx.Response(200, json={"Items": [{"itemPrice": 10000}]}))
    await client.post(f"/api/tracked-products/{product_id}/collect-price", headers=headers)
    assert sent_to == []

    route.mock(return_value=httpx.Response(200, json={"Items": [{"itemPrice": 8500}]}))
    await client.post(f"/api/tracked-products/{product_id}/collect-price", headers=headers)
    assert sent_to == ["notify3@example.com"]
