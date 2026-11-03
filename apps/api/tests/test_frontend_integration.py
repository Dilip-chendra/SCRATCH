import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_frontend_auth_contract(client: AsyncClient, seed_data):
    """Verify that backend responses conform exactly to frontend Next.js contract expectations."""
    payload = {
        "email": "user_a@company-a.com",
        "password": "Password123!"
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200

    data = response.json()
    # Frontend AuthContext expects these exact keys
    assert "access_token" in data
    assert "csrf_token" in data
    assert "user" in data
    assert "workspaces" in data
    assert "id" in data["user"]
    assert "email" in data["user"]
    assert "full_name" in data["user"]

    # Workspaces array contract
    for ws in data["workspaces"]:
        assert "id" in ws
        assert "name" in ws
        assert "role" in ws


@pytest.mark.asyncio
async def test_frontend_csrf_protection_on_mutations(client: AsyncClient, seed_data):
    """
    Verify CSRF protection for cookie-authenticated clients:
    If client presents access_token cookie, state-changing requests MUST include matching X-CSRF-Token.
    """
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "user_a@company-a.com", "password": "Password123!"}
    )
    access_token = login_res.cookies.get("access_token")
    csrf_token = login_res.cookies.get("csrf_token")
    ws_a = seed_data["ws_a"]

    # Request with missing X-CSRF-Token header -> Rejected 403
    rejected_res = await client.patch(
        "/api/v1/workspaces/current",
        cookies={"access_token": access_token, "csrf_token": csrf_token},
        headers={"X-Workspace-ID": str(ws_a.id)},
        json={"name": "Attacker Name"}
    )
    assert rejected_res.status_code == 403
    assert "CSRF validation failed" in rejected_res.json()["detail"]

    # Request with matching X-CSRF-Token header -> Accepted 200
    accepted_res = await client.patch(
        "/api/v1/workspaces/current",
        cookies={"access_token": access_token, "csrf_token": csrf_token},
        headers={
            "X-Workspace-ID": str(ws_a.id),
            "X-CSRF-Token": csrf_token
        },
        json={"name": "Legitimate User Name"}
    )
    assert accepted_res.status_code == 200
    assert accepted_res.json()["name"] == "Legitimate User Name"
