import json
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.core.security import create_access_token
from app.models.leads import Company, Contact, ImportBatch
from app.models.tenancy import WorkspaceMembership, WorkspaceRole


@pytest.mark.asyncio
async def test_consumer_webmail_ingestion_remediation(client: AsyncClient, seed_data, db_session):
    """
    Comprehensive regression test verifying the fix for DEF-02:
    - Consumer webmail emails (gmail.com, yahoo.com) without company domains do NOT create company records.
    - Contact is preserved with company_id = None.
    - Rows are reported as VALID.
    - Explicit corporate domains alongside webmail emails properly associate.
    - Corporate emails properly create company records.
    - Repeated imports properly detect duplicates.
    """
    user_a_id = seed_data["user_a_id"]
    ws_a_id = seed_data["ws_a_id"]

    token = create_access_token(subject=str(user_a_id))
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(ws_a_id),
    }

    # CSV containing:
    # Row 1: Gmail user with NO company domain -> Contact created, NO company created
    # Row 2: Yahoo user with explicit company domain -> Company created, Contact linked
    # Row 3: Corporate user with NO company domain -> Company extracted from email, Contact linked
    # Row 4: Outlook user with NO company domain -> Contact created, NO company created
    csv_content = (
        "Company Name,Company Website,Work Email,Full Name,Job Title\n"
        ",,freelancer1@gmail.com,Alice Walker,Independent Consultant\n"
        "Startup Co,https://startup.io,founder@yahoo.com,Bob Smith,Founder\n"
        ",,engineer@linear.app,Charlie Brown,Staff Engineer\n"
        ",,creator@outlook.com,Diana Prince,Content Creator\n"
    ).encode("utf-8")

    column_mapping = {
        "company_name": "Company Name",
        "domain": "Company Website",
        "email": "Work Email",
        "full_name": "Full Name",
        "title": "Job Title",
    }

    files = {"file": ("leads_webmail.csv", csv_content, "text/csv")}
    data = {"column_mapping": json.dumps(column_mapping)}

    res = await client.post("/api/v1/leads/import", files=files, data=data, headers=headers)
    assert res.status_code == 200, res.text
    result = res.json()

    # All 4 rows must be validly ingested
    assert result["total_rows"] == 4
    assert result["valid_rows"] == 4
    assert result["duplicate_rows"] == 0
    assert result["suppressed_rows"] == 0
    assert result["error_rows"] == 0

    # Verify Database State:
    # 1. NO company with domain 'gmail.com', 'yahoo.com', or 'outlook.com' exists
    comp_stmt = select(Company).where(Company.workspace_id == ws_a_id)
    comp_res = await db_session.execute(comp_stmt)
    companies = comp_res.scalars().all()
    company_domains = {c.normalized_domain for c in companies}

    assert "gmail.com" not in company_domains, "DEF-02 FAILURE: 'gmail.com' company was created!"
    assert "yahoo.com" not in company_domains, "DEF-02 FAILURE: 'yahoo.com' company was created!"
    assert "outlook.com" not in company_domains, "DEF-02 FAILURE: 'outlook.com' company was created!"
    assert "startup.io" in company_domains, "Expected explicit domain 'startup.io' company"
    assert "linear.app" in company_domains, "Expected corporate email domain 'linear.app' company"
    assert len(companies) == 2, f"Expected exactly 2 companies, found {len(companies)}"

    # 2. Verify Contacts:
    contact_stmt = select(Contact).where(Contact.workspace_id == ws_a_id)
    contact_res = await db_session.execute(contact_stmt)
    contacts = {c.email: c for c in contact_res.scalars().all()}

    # Alice (gmail) -> contact exists, company_id is None
    assert "freelancer1@gmail.com" in contacts
    assert contacts["freelancer1@gmail.com"].company_id is None

    # Diana (outlook) -> contact exists, company_id is None
    assert "creator@outlook.com" in contacts
    assert contacts["creator@outlook.com"].company_id is None

    # Bob (yahoo with explicit domain startup.io) -> linked to startup.io company
    startup_company = next(c for c in companies if c.normalized_domain == "startup.io")
    assert "founder@yahoo.com" in contacts
    assert contacts["founder@yahoo.com"].company_id == startup_company.id

    # Charlie (linear.app corporate email) -> linked to linear.app company
    linear_company = next(c for c in companies if c.normalized_domain == "linear.app")
    assert "engineer@linear.app" in contacts
    assert contacts["engineer@linear.app"].company_id == linear_company.id

    # 3. Test Deduplication on re-import
    reimport_res = await client.post(
        "/api/v1/leads/import",
        files={"file": ("leads_webmail_retry.csv", csv_content, "text/csv")},
        data=data,
        headers=headers,
    )
    assert reimport_res.status_code == 200
    retry_data = reimport_res.json()
    assert retry_data["valid_rows"] == 0
    assert retry_data["duplicate_rows"] == 4


@pytest.mark.asyncio
async def test_read_only_role_rejected_on_phase1_mutations(client: AsyncClient, seed_data, db_session):
    """
    Verifies that a workspace member with READ_ONLY role is rejected with HTTP 403 Forbidden
    when attempting Phase 1 mutating actions (addressing DEF-03).
    """
    user_b_id = seed_data["user_b_id"]
    ws_b_id = seed_data["ws_b_id"]

    # Update User B's membership to READ_ONLY
    stmt = select(WorkspaceMembership).where(
        WorkspaceMembership.user_id == user_b_id,
        WorkspaceMembership.workspace_id == ws_b_id,
    )
    res = await db_session.execute(stmt)
    membership = res.scalar_one()
    membership.role = WorkspaceRole.READ_ONLY
    await db_session.commit()

    token = create_access_token(subject=str(user_b_id))
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(ws_b_id),
    }

    # 1. PUT /api/v1/business-profile -> 403 Forbidden
    res = await client.put(
        "/api/v1/business-profile",
        json={"company_name": "Unauthorized Edit"},
        headers=headers,
    )
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"
    assert "requires minimum 'MEMBER' role" in res.json()["detail"]

    # 2. POST /api/v1/suppression -> 403 Forbidden
    res = await client.post(
        "/api/v1/suppression",
        json={"type": "DOMAIN", "value": "test.com"},
        headers=headers,
    )
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"

    # 3. POST /api/v1/leads/import -> 403 Forbidden
    csv_bytes = b"Company,Website,Email\nAcme,acme.com,a@acme.com\n"
    res = await client.post(
        "/api/v1/leads/import",
        files={"file": ("test.csv", csv_bytes, "text/csv")},
        data={"column_mapping": json.dumps({"domain": "Website", "email": "Email"})},
        headers=headers,
    )
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"
