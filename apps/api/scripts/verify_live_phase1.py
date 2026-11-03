"""
SCRATCH — Phase 1 Live Integration Verification Script
======================================================
Executes end-to-end live verification of Phase 1 against running PostgreSQL 16,
FastAPI, and Redis instances.

Checks:
1. User registration & workspace bootstrap via live FastAPI.
2. PostgreSQL 16 RLS verification with non-superuser role `scratch_app` on Phase 1 tables.
3. Business Profile configuration & persistence (PUT & GET /api/v1/business-profile).
4. Suppression list management (POST, GET, and suppression enforcement).
5. Lead file upload & column auto-mapping preview (POST /api/v1/leads/upload).
6. Streaming lead ingestion with deduplication and suppression filtering (POST /api/v1/leads/import).
7. Row-level quarantine and audit inspection (GET /api/v1/leads/batches/{id}/rows).
8. Accounts/Companies and Contacts directory search & pagination.
9. Deterministic deduplication verification on repeated import.
"""

import asyncio
import json
import os
import sys
import uuid
import asyncpg
import httpx

API_BASE = "http://localhost:8000"
PG_URL_APP = "postgresql://scratch_app:app_local_secret_change_me@localhost:5432/scratch"


async def main():
    print("=" * 70)
    print("SCRATCH PHASE 1 LIVE INTEGRATION VERIFICATION")
    print("=" * 70)

    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        # Step 1: Health check
        print("\n[1/7] Probing API Health...")
        health_res = await client.get("/health")
        assert health_res.status_code == 200, f"Health failed: {health_res.text}"
        print("  -> FastAPI & Redis live and healthy.")

        # Step 2: Register user and obtain workspace
        print("\n[2/7] Authenticating test user and bootstrapping workspace...")
        unique_suffix = uuid.uuid4().hex[:6]
        user_email = f"lead-admin-{unique_suffix}@scratch-test.io"
        reg_payload = {
            "email": user_email,
            "password": "SecurePassword123!",
            "full_name": "Phase1 Verifier",
            "organization_name": f"P1 Org {unique_suffix}"
        }
        reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
        assert reg_res.status_code == 201, f"Register failed: {reg_res.text}"
        reg_data = reg_res.json()
        user_id = reg_data["user"]["id"]
        workspace_id = reg_data["workspaces"][0]["id"]
        csrf_token = reg_data["csrf_token"]
        
        headers = {
            "X-Workspace-ID": workspace_id,
            "X-CSRF-Token": csrf_token or "",
        }
        print(f"  -> User registered: {user_email}")
        print(f"  -> Workspace ID: {workspace_id}")

        # Step 3: Verify PostgreSQL RLS with `scratch_app` role
        print("\n[3/7] Verifying live PostgreSQL RLS with non-superuser role (scratch_app)...")
        conn = await asyncpg.connect(PG_URL_APP)
        try:
            # Under tenant context of this workspace
            async with conn.transaction():
                await conn.execute("SELECT set_config('app.current_tenant_id', $1, true)", workspace_id)
                await conn.execute("""
                    INSERT INTO companies (id, workspace_id, name, domain, normalized_domain, status, custom_attributes, created_at, updated_at)
                    VALUES ($1, $2, 'RLS Canary Co', 'canary.com', 'canary.com', 'ACTIVE', '{}'::json, NOW(), NOW())
                """, uuid.uuid4(), uuid.UUID(workspace_id))
                
                rows = await conn.fetch("SELECT name FROM companies")
                assert len(rows) >= 1, "Should see inserted company under own tenant context"

            # Under a DIFFERENT tenant context
            other_ws_id = str(uuid.uuid4())
            async with conn.transaction():
                await conn.execute("SELECT set_config('app.current_tenant_id', $1, true)", other_ws_id)
                cross_rows = await conn.fetch("SELECT name FROM companies")
                assert len(cross_rows) == 0, f"Cross-tenant leak! Expected 0 rows, got {len(cross_rows)}"

            # Without tenant context (fails closed)
            async with conn.transaction():
                await conn.execute("SELECT set_config('app.current_tenant_id', '', true)")
                closed_rows = await conn.fetch("SELECT name FROM companies")
                assert len(closed_rows) == 0, f"Missing context failed to close! Got {len(closed_rows)}"

            print("  -> PostgreSQL RLS isolation verified: Own context OK, cross-tenant 0 rows, missing context 0 rows.")
        finally:
            await conn.close()

        # Step 4: Configure Business Profile
        print("\n[4/7] Testing Business Profile configuration (PUT /api/v1/business-profile)...")
        profile_data = {
            "company_name": "HyperScale Tech",
            "website_url": "https://hyperscale.tech",
            "industry": "Cloud Infrastructure",
            "products_services": [{"name": "Cluster Optimizer", "price": "1000/mo"}],
            "value_propositions": ["Save 45% on compute", "Sub-second autoscaling"],
            "target_industries": ["Fintech", "SaaS", "E-commerce"],
            "ideal_customer_profiles": [{"title": "VP Infrastructure", "min_headcount": 100}],
            "disqualification_rules": ["Zero Kubernetes usage", "Students / Hobbyists"]
        }
        prof_res = await client.put("/api/v1/business-profile", json=profile_data, headers=headers)
        assert prof_res.status_code == 200, f"Profile PUT failed: {prof_res.text}"
        
        prof_get = await client.get("/api/v1/business-profile", headers=headers)
        assert prof_get.status_code == 200
        assert prof_get.json()["company_name"] == "HyperScale Tech"
        print("  -> Business Profile updated and verified.")

        # Step 5: Add Suppression Entry
        print("\n[5/7] Testing Suppression list management (POST /api/v1/suppression)...")
        supp_data = {
            "type": "DOMAIN",
            "value": "https://www.rival-cloud.io/contact",
            "reason": "Direct Rival Vendor"
        }
        supp_res = await client.post("/api/v1/suppression", json=supp_data, headers=headers)
        assert supp_res.status_code == 201, f"Suppression failed: {supp_res.text}"
        assert supp_res.json()["value"] == "rival-cloud.io"

        supp_list = await client.get("/api/v1/suppression", headers=headers)
        assert supp_list.status_code == 200
        assert any(e["value"] == "rival-cloud.io" for e in supp_list.json())
        print("  -> Domain 'rival-cloud.io' added to suppression list.")

        # Step 6: File Preview & Streaming Import
        print("\n[6/7] Testing CSV Lead Preview and Streaming Ingestion...")
        csv_sample = (
            "Account,Web URL,Contact Email,Full Name,Title,City\n"
            "Datadog Inc,https://www.datadoghq.com,devops-lead@datadoghq.com,Rachel Green,Director of SRE,New York\n"
            "Rival Cloud,https://rival-cloud.io/features,competitor@rival-cloud.io,Monica Geller,Head of Sales,Boston\n"
            "Snowflake Co,snowflake.com,data-arch@snowflake.com,Chandler Bing,Principal Architect,San Mateo\n"
            ",,,,,\n"
            "Incomplete Record Without Domain Or Email,,,,,\n"
        ).encode("utf-8")

        # Upload Preview
        upload_res = await client.post(
            "/api/v1/leads/upload",
            files={"file": ("prospects.csv", csv_sample, "text/csv")},
            headers=headers
        )
        assert upload_res.status_code == 200, f"Upload preview failed: {upload_res.text}"
        preview = upload_res.json()
        assert preview["suggested_mappings"]["company_name"] == "Account"
        assert preview["suggested_mappings"]["domain"] == "Web URL"
        assert preview["suggested_mappings"]["email"] == "Contact Email"
        print(f"  -> File analyzed: {preview['total_estimated_rows']} estimated rows, headers auto-mapped.")

        # Commit Import
        col_mapping = {
            "company_name": "Account",
            "domain": "Web URL",
            "email": "Contact Email",
            "full_name": "Full Name",
            "title": "Title",
            "city": "City"
        }
        import_res = await client.post(
            "/api/v1/leads/import",
            files={"file": ("prospects.csv", csv_sample, "text/csv")},
            data={"column_mapping": json.dumps(col_mapping)},
            headers=headers
        )
        assert import_res.status_code == 200, f"Import failed: {import_res.text}"
        batch = import_res.json()
        print(f"  -> Import Batch Summary: Total={batch['total_rows']}, Valid={batch['valid_rows']}, Suppressed={batch['suppressed_rows']}, Error={batch['error_rows']}, Duplicate={batch['duplicate_rows']}")
        assert batch["valid_rows"] == 2, f"Expected 2 valid rows, got {batch['valid_rows']}"
        assert batch["suppressed_rows"] == 1, f"Expected 1 suppressed row, got {batch['suppressed_rows']}"
        assert batch["error_rows"] == 1, f"Expected 1 error row, got {batch['error_rows']}"

        # Inspect Quarantine Rows
        batch_id = batch["batch_id"]
        quarantine_res = await client.get(f"/api/v1/leads/batches/{batch_id}/rows?status_filter=SUPPRESSED", headers=headers)
        assert quarantine_res.status_code == 200
        assert len(quarantine_res.json()) == 1
        assert "Direct Rival Vendor" in quarantine_res.json()[0]["error_details"]["reason"]

        # Step 7: Deduplication & Directory Queries
        print("\n[7/7] Verifying Deduplication on re-import and Directory search...")
        reimport_res = await client.post(
            "/api/v1/leads/import",
            files={"file": ("prospects_retry.csv", csv_sample, "text/csv")},
            data={"column_mapping": json.dumps(col_mapping)},
            headers=headers
        )
        assert reimport_res.status_code == 200
        re_batch = reimport_res.json()
        assert re_batch["valid_rows"] == 0
        assert re_batch["duplicate_rows"] == 2
        print(f"  -> Idempotent re-import: Valid=0, Duplicates={re_batch['duplicate_rows']}, Suppressed={re_batch['suppressed_rows']}")

        # Directory search: Companies
        comps_res = await client.get("/api/v1/leads/companies?query=datadog", headers=headers)
        assert comps_res.status_code == 200
        assert len(comps_res.json()) == 1
        assert comps_res.json()[0]["normalized_domain"] == "datadoghq.com"

        # Directory search: Contacts
        contacts_res = await client.get("/api/v1/leads/contacts?query=chandler", headers=headers)
        assert contacts_res.status_code == 200
        assert len(contacts_res.json()) == 1
        assert contacts_res.json()[0]["email"] == "data-arch@snowflake.com"
        assert contacts_res.json()[0]["first_name"] == "Chandler"
        assert contacts_res.json()[0]["last_name"] == "Bing"
        print("  -> Directory search verified for both companies and contacts.")

    print("\n" + "=" * 70)
    print("ALL PHASE 1 LIVE INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
