import json
import uuid
import pytest
from httpx import AsyncClient
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_lead_ingestion_end_to_end(client: AsyncClient, seed_data):
    """
    Comprehensive test of the complete Phase 1 ingestion flow:
    - Business profile configuration
    - Suppression entry creation
    - CSV preview and column auto-mapping
    - Streaming lead import with deduplication and suppression filtering
    - Companies and contacts directory query
    - Row-level quarantine inspection
    """
    user_a_id = seed_data["user_a_id"]
    ws_a_id = seed_data["ws_a_id"]

    # Generate Auth Token
    access_token = create_access_token(subject=str(user_a_id))
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Workspace-ID": str(ws_a_id),
    }

    # Step 1: Configure Business Profile
    profile_payload = {
        "company_name": "CloudScale AI",
        "website_url": "https://cloudscale.ai",
        "industry": "Enterprise Software",
        "products_services": [{"name": "AI Pipeline", "tier": "Enterprise"}],
        "value_propositions": ["Reduce ops costs by 60%", "Zero latency"],
        "target_industries": ["Fintech", "Healthtech", "DevOps"],
        "ideal_customer_profiles": [{"role": "CTO", "company_size": "50-500"}],
        "disqualification_rules": ["B2C focus", "No engineering team"],
    }
    res = await client.put("/api/v1/business-profile", json=profile_payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["company_name"] == "CloudScale AI"
    assert len(data["value_propositions"]) == 2

    # Verify GET business profile
    res = await client.get("/api/v1/business-profile", headers=headers)
    assert res.status_code == 200
    assert res.json()["company_name"] == "CloudScale AI"

    # Step 2: Add Suppression Entry for competitor domain
    suppress_payload = {
        "type": "DOMAIN",
        "value": "https://www.competitor-cloud.com/about",
        "reason": "Direct Competitor Exclusion"
    }
    res = await client.post("/api/v1/suppression", json=suppress_payload, headers=headers)
    assert res.status_code == 201, res.text
    suppress_entry = res.json()
    assert suppress_entry["value"] == "competitor-cloud.com"
    assert suppress_entry["reason"] == "Direct Competitor Exclusion"

    # List suppression entries
    res = await client.get("/api/v1/suppression", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # Step 3: Preview Uploaded CSV
    csv_content = (
        "Company Name,Company Website,Work Email,Full Name,Job Title,City\n"
        "Acme Innovations,https://www.acme-innovations.com/us,alice@acme-innovations.com,Alice Walker,VP of Engineering,San Francisco\n"
        "Competitor Cloud,competitor-cloud.com,sales@competitor-cloud.com,Bob Ross,Head of Sales,Austin\n"
        "Beta Systems,https://betasystems.io,charlie@betasystems.io,Charlie Brown,CTO,New York\n"
        ",,,,\n"  # Empty row
        "Invalid Row Missing Data,,,,,\n"  # No domain, company or email
    ).encode("utf-8")

    files = {"file": ("leads.csv", csv_content, "text/csv")}
    res = await client.post("/api/v1/leads/upload", files=files, headers=headers)
    assert res.status_code == 200, res.text
    preview = res.json()
    assert preview["filename"] == "leads.csv"
    assert "Company Name" in preview["headers"]
    assert preview["suggested_mappings"]["company_name"] == "Company Name"
    assert preview["suggested_mappings"]["domain"] == "Company Website"
    assert preview["suggested_mappings"]["email"] == "Work Email"

    # Step 4: Execute Import
    column_mapping = {
        "company_name": "Company Name",
        "domain": "Company Website",
        "email": "Work Email",
        "full_name": "Full Name",
        "title": "Job Title",
        "city": "City",
    }
    import_files = {"file": ("leads.csv", csv_content, "text/csv")}
    import_data = {"column_mapping": json.dumps(column_mapping)}
    res = await client.post("/api/v1/leads/import", files=import_files, data=import_data, headers=headers)
    assert res.status_code == 200, res.text
    import_result = res.json()

    assert import_result["total_rows"] == 4
    assert import_result["valid_rows"] == 2
    assert import_result["suppressed_rows"] == 1
    assert import_result["error_rows"] == 1
    assert import_result["duplicate_rows"] == 0

    batch_id = import_result["batch_id"]

    # Step 5: Verify Import Batches List and Row Quarantine
    res = await client.get("/api/v1/leads/batches", headers=headers)
    assert res.status_code == 200
    batches = res.json()
    assert len(batches) >= 1
    assert batches[0]["batch_id"] == batch_id

    # Query suppressed rows
    res = await client.get(f"/api/v1/leads/batches/{batch_id}/rows?status_filter=SUPPRESSED", headers=headers)
    assert res.status_code == 200
    suppressed_rows = res.json()
    assert len(suppressed_rows) == 1
    assert "Direct Competitor Exclusion" in suppressed_rows[0]["error_details"]["reason"]

    # Query error rows
    res = await client.get(f"/api/v1/leads/batches/{batch_id}/rows?status_filter=ERROR", headers=headers)
    assert res.status_code == 200
    error_rows = res.json()
    assert len(error_rows) == 1

    # Step 6: Verify Deduplication on Second Import
    # If we re-import the exact same file, previously valid rows should now be DUPLICATE
    import_files_2 = {"file": ("leads_retry.csv", csv_content, "text/csv")}
    res = await client.post("/api/v1/leads/import", files=import_files_2, data=import_data, headers=headers)
    assert res.status_code == 200
    retry_result = res.json()
    assert retry_result["valid_rows"] == 0
    assert retry_result["duplicate_rows"] == 2
    assert retry_result["suppressed_rows"] == 1

    # Step 7: Verify Directory Queries
    # Companies
    res = await client.get("/api/v1/leads/companies", headers=headers)
    assert res.status_code == 200
    companies = res.json()
    assert len(companies) == 2
    domains = {c["normalized_domain"] for c in companies}
    assert "acme-innovations.com" in domains
    assert "betasystems.io" in domains

    # Search company by query
    res = await client.get("/api/v1/leads/companies?query=acme", headers=headers)
    assert res.status_code == 200
    acme_results = res.json()
    assert len(acme_results) == 1
    assert acme_results[0]["normalized_domain"] == "acme-innovations.com"

    # Contacts
    res = await client.get("/api/v1/leads/contacts", headers=headers)
    assert res.status_code == 200
    contacts = res.json()
    assert len(contacts) == 2
    contact_emails = {c["email"] for c in contacts}
    assert "alice@acme-innovations.com" in contact_emails
    assert "charlie@betasystems.io" in contact_emails

    # Search contact by query
    res = await client.get("/api/v1/leads/contacts?query=charlie", headers=headers)
    assert res.status_code == 200
    charlie_results = res.json()
    assert len(charlie_results) == 1
    assert charlie_results[0]["email"] == "charlie@betasystems.io"
    assert charlie_results[0]["first_name"] == "Charlie"
    assert charlie_results[0]["last_name"] == "Brown"
