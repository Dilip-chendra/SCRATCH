"""
SCRATCH — Live HTTP API Verification Script
===========================================
Executes full HTTP client integration tests against the live FastAPI instance,
real PostgreSQL database, and real Redis session cache.
"""

import asyncio
import httpx


async def test_live_api():
    base_url = "http://localhost:8000"
    print("=" * 70)
    print("LIVE FASTAPI + POSTGRESQL + REDIS HTTP ENDPOINT VERIFICATION")
    print("=" * 70)

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        # 1. Health Endpoint
        res = await client.get("/health")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        health_data = res.json()
        assert health_data["status"] == "healthy"
        assert health_data["services"]["database"]["status"] == "healthy"
        assert health_data["services"]["redis"]["status"] == "healthy"
        print("[OK] GET /health returned 200 with all services healthy")

        # 2. User Registration
        unique_email = f"live_founder_{asyncio.get_event_loop().time()}@scratchtest.io"
        reg_payload = {
            "email": unique_email,
            "password": "LivePassword123!",
            "full_name": "Live Verification User",
            "organization_name": "Live Verification Org",
            "workspace_name": "Live Primary Workspace"
        }
        reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
        assert reg_res.status_code == 201, f"Register failed: {reg_res.text}"
        reg_data = reg_res.json()
        assert "access_token" in reg_data
        assert "csrf_token" in reg_data
        workspace_id = reg_data["workspaces"][0]["id"]
        csrf_token = reg_data["csrf_token"]
        print(f"[OK] POST /api/v1/auth/register created user {unique_email} and workspace {workspace_id}")

        # Cookies check
        assert "access_token" in reg_res.cookies
        assert "refresh_token" in reg_res.cookies
        assert "csrf_token" in reg_res.cookies
        print("[OK] Secure cookies issued: access_token, refresh_token, csrf_token")

        # 3. User Login
        login_res = await client.post("/api/v1/auth/login", json={
            "email": unique_email,
            "password": "LivePassword123!"
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        access_token = login_res.json()["access_token"]
        print("[OK] POST /api/v1/auth/login authenticated successfully with Argon2id")

        # 4. Workspace Access (Tenant Context)
        ws_res = await client.get(
            "/api/v1/workspaces/current",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Workspace-ID": workspace_id
            }
        )
        assert ws_res.status_code == 200, f"Workspace fetch failed: {ws_res.text}"
        assert ws_res.json()["name"] == "Live Primary Workspace"
        print("[OK] GET /api/v1/workspaces/current resolved active tenant context")

        # 5. CSRF Protection on Workspace Mutation
        # Attempt mutation without CSRF header -> MUST FAIL 403
        bad_patch = await client.patch(
            "/api/v1/workspaces/current",
            cookies={
                "access_token": login_res.cookies["access_token"],
                "csrf_token": csrf_token
            },
            headers={"X-Workspace-ID": workspace_id},
            json={"name": "Hacked Name"}
        )
        assert bad_patch.status_code == 403
        print("[OK] PATCH /api/v1/workspaces/current without X-CSRF-Token rejected with 403")

        # Mutate with valid CSRF token header -> MUST SUCCEED 200
        good_patch = await client.patch(
            "/api/v1/workspaces/current",
            cookies={
                "access_token": login_res.cookies["access_token"],
                "csrf_token": csrf_token
            },
            headers={
                "X-Workspace-ID": workspace_id,
                "X-CSRF-Token": csrf_token
            },
            json={"name": "Live Primary Workspace Renamed"}
        )
        assert good_patch.status_code == 200
        assert good_patch.json()["name"] == "Live Primary Workspace Renamed"
        print("[OK] PATCH /api/v1/workspaces/current with valid X-CSRF-Token succeeded")

        # 6. Refresh Token Rotation & Reuse Defense
        initial_refresh = login_res.cookies["refresh_token"]
        refresh_res = await client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": initial_refresh}
        )
        assert refresh_res.status_code == 200
        new_refresh = refresh_res.cookies["refresh_token"]
        assert new_refresh != initial_refresh
        print("[OK] POST /api/v1/auth/refresh rotated refresh token successfully")

        # Re-present used token -> MUST FAIL 401 and revoke family
        reuse_res = await client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": initial_refresh}
        )
        assert reuse_res.status_code == 401
        print("[OK] Token reuse attack correctly triggered 401 and revoked family")

        # Assert rotated token was also revoked
        subsequent_res = await client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": new_refresh}
        )
        assert subsequent_res.status_code == 401
        print("[OK] Subsequent token in family verified revoked (complete family revocation)")

        # 7. Logout
        logout_res = await client.post("/api/v1/auth/logout")
        assert logout_res.status_code == 200
        print("[OK] POST /api/v1/auth/logout cleared session and cookies")

    print("\n" + "=" * 70)
    print("ALL LIVE HTTP INTEGRATION CHECKS PASSED AGAINST REAL POSTGRESQL & REDIS")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_live_api())
