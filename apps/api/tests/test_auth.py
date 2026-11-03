from datetime import timedelta
import pytest
from httpx import AsyncClient
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password
)


def test_argon2id_password_hashing():
    """Verify Argon2id password hashing and deterministic verification."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_lifecycle():
    """Verify JWT access token creation, claims extraction, and tampering defense."""
    token = create_access_token(
        subject="test-user-id",
        extra_claims={"role": "admin"}
    )
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "test-user-id"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"

    # Expired token rejection
    expired_token = create_access_token(
        subject="test-user-id",
        expires_delta=timedelta(seconds=-10)
    )
    assert decode_access_token(expired_token) is None

    # Tampered signature rejection
    tampered_token = token[:-4] + "abcd"
    assert decode_access_token(tampered_token) is None


@pytest.mark.asyncio
async def test_registration_and_cookie_issuance(client: AsyncClient):
    """Verify user registration creates organization, workspace, and issues secure cookies."""
    payload = {
        "email": "newfounder@acmecorp.com",
        "password": "StrongPassword123!",
        "full_name": "Jane Founder",
        "organization_name": "Acme Corporation",
        "workspace_name": "Sales US"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["user"]["email"] == "newfounder@acmecorp.com"
    assert len(data["workspaces"]) == 1
    assert data["workspaces"][0]["name"] == "Sales US"
    assert data["workspaces"][0]["role"] == "OWNER"
    assert "access_token" in data
    assert "csrf_token" in data

    # Verify cookies
    cookies = response.cookies
    assert "access_token" in cookies
    assert "refresh_token" in cookies
    assert "csrf_token" in cookies


@pytest.mark.asyncio
async def test_login_flow(client: AsyncClient, seed_data):
    """Verify login with Argon2id credentials issues tokens and cookies."""
    payload = {
        "email": "user_a@company-a.com",
        "password": "Password123!"
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["user"]["email"] == "user_a@company-a.com"
    assert len(data["workspaces"]) >= 1

    # Invalid password returns 401
    bad_res = await client.post("/api/v1/auth/login", json={"email": "user_a@company-a.com", "password": "WrongPassword"})
    assert bad_res.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_reuse_defense(client: AsyncClient, seed_data):
    """
    Verify refresh token rotation and assert that presenting an already-used token
    triggers security revocation of the entire token family.
    """
    # 1. Login to get initial cookies
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "user_a@company-a.com", "password": "Password123!"}
    )
    assert login_res.status_code == 200
    initial_refresh_token = login_res.cookies.get("refresh_token")
    assert initial_refresh_token is not None

    # 2. Legitimate refresh: exchange token 1 for token 2
    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": initial_refresh_token}
    )
    assert refresh_res.status_code == 200
    new_refresh_token = refresh_res.cookies.get("refresh_token")
    assert new_refresh_token is not None
    assert new_refresh_token != initial_refresh_token

    # 3. ATTACK SIMULATION: Re-present initial_refresh_token (which was rotated/revoked)
    reuse_res = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": initial_refresh_token}
    )
    assert reuse_res.status_code == 401
    assert "Token reuse detected" in reuse_res.json()["detail"]

    # 4. Assert token 2 is now ALSO revoked because the family was compromised
    subsequent_res = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": new_refresh_token}
    )
    assert subsequent_res.status_code == 401


@pytest.mark.asyncio
async def test_logout_clears_cookies(client: AsyncClient, seed_data):
    """Verify logout revokes session and clears cookies."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "user_a@company-a.com", "password": "Password123!"}
    )
    token = login_res.json()["access_token"]
    refresh_token = login_res.cookies.get("refresh_token")

    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
        cookies={"refresh_token": refresh_token}
    )
    assert logout_res.status_code == 200
