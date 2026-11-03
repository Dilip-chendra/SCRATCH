import uuid
import pytest
from httpx import AsyncClient
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_empty_string_workspace_id_rejected(client: AsyncClient, seed_data):
    """Verify that an empty string in X-Workspace-ID is rejected as Bad Request."""
    user_a_id = seed_data["user_a_id"]
    token = create_access_token(subject=str(user_a_id))

    response = await client.get(
        "/api/v1/workspaces/current",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Workspace-ID": ""
        }
    )
    assert response.status_code == 400
    assert "X-Workspace-ID header is required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_malformed_uuid_workspace_id_rejected(client: AsyncClient, seed_data):
    """Verify that a malformed non-UUID string in X-Workspace-ID is rejected."""
    user_a_id = seed_data["user_a_id"]
    token = create_access_token(subject=str(user_a_id))

    response = await client.get(
        "/api/v1/workspaces/current",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Workspace-ID": "invalid-not-a-uuid"
        }
    )
    assert response.status_code == 400
    assert "Invalid X-Workspace-ID header format" in response.json()["detail"]


@pytest.mark.asyncio
async def test_random_unassociated_uuid_workspace_id_rejected(client: AsyncClient, seed_data):
    """Verify that a syntactically valid but unassociated UUID returns 403 Forbidden."""
    user_a_id = seed_data["user_a_id"]
    random_ws_id = uuid.uuid4()
    token = create_access_token(subject=str(user_a_id))

    response = await client.get(
        "/api/v1/workspaces/current",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Workspace-ID": str(random_ws_id)
        }
    )
    assert response.status_code == 403
    assert "User does not have active membership" in response.json()["detail"]
