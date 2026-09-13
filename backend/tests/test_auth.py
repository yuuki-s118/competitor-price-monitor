import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_login_and_read_me(client: AsyncClient) -> None:
    email = "tester@example.com"
    password = "correct-horse-battery-staple"

    register_response = await client.post(
        "/api/auth/register", json={"email": email, "password": password}
    )
    assert register_response.status_code == 201
    assert register_response.json()["email"] == email

    login_response = await client.post(
        "/api/auth/login", data={"username": email, "password": password}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email


@pytest.mark.asyncio
async def test_login_with_wrong_password_is_rejected(client: AsyncClient) -> None:
    email = "tester2@example.com"
    await client.post(
        "/api/auth/register", json={"email": email, "password": "correct-password"}
    )

    response = await client.post(
        "/api/auth/login", data={"username": email, "password": "wrong-password"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_without_token_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/api/auth/me")
    assert response.status_code == 401
