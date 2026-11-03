import pytest
from httpx import AsyncClient
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_authorized_workspace_access(client: AsyncClient, seed_data):
    """Verify that a user can access a workspace where they possess active membership."""
    user_a_id = seed_data["user_a_id"]
    ws_a_id = seed_data["ws_a_id"]
    token = create_access_token(subject=str(user_a_id))

    response = await client.get(
        "/api/v1/workspaces/current",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Workspace-ID": str(ws_a_id)
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(ws_a_id)
    assert data["role"] == "OWNER"


@pytest.mark.asyncio
async def test_unauthorized_cross_workspace_access_rejected(client: AsyncClient, seed_data):
    """Verify that User A attempting to access Workspace B returns 403 Forbidden."""
    user_a_id = seed_data["user_a_id"]
    ws_b_id = seed_data["ws_b_id"]
    token = create_access_token(subject=str(user_a_id))

    response = await client.get(
        "/api/v1/workspaces/current",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Workspace-ID": str(ws_b_id)
        }
    )
    assert response.status_code == 403
    assert "User does not have active membership in the specified workspace" in response.json()["detail"]


@pytest.mark.asyncio
async def test_missing_workspace_header_rejected(client: AsyncClient, seed_data):
    """Verify that omitting X-Workspace-ID returns 400 Bad Request."""
    user_a_id = seed_data["user_a_id"]
    token = create_access_token(subject=str(user_a_id))

    response = await client.get(
        "/api/v1/workspaces/current",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "X-Workspace-ID header is required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_rbac_role_enforcement(client: AsyncClient, seed_data):
    """
    Verify RBAC permission hierarchy:
    - User B (MEMBER role in Workspace B) cannot mutate workspace (requires ADMIN).
    - User A (OWNER role in Workspace A) can mutate workspace.
    """
    user_b_id = seed_data["user_b_id"]
    ws_b_id = seed_data["ws_b_id"]
    token_b = create_access_token(subject=str(user_b_id))

    # User B mutation rejected
    patch_b = await client.patch(
        "/api/v1/workspaces/current",
        headers={
            "Authorization": f"Bearer {token_b}",
            "X-Workspace-ID": str(ws_b_id)
        },
        json={"name": "Hacked Name"}
    )
    assert patch_b.status_code == 403
    assert "Action requires minimum 'ADMIN' role" in patch_b.json()["detail"]

    # User A mutation accepted
    user_a_id = seed_data["user_a_id"]
    ws_a_id = seed_data["ws_a_id"]
    token_a = create_access_token(subject=str(user_a_id))

    patch_a = await client.patch(
        "/api/v1/workspaces/current",
        headers={
            "Authorization": f"Bearer {token_a}",
            "X-Workspace-ID": str(ws_a_id)
        },
        json={"name": "Renamed Workspace A"}
    )
    assert patch_a.status_code == 200
    assert patch_a.json()["name"] == "Renamed Workspace A"
