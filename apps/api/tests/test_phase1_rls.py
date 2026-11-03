import uuid
import pytest
from sqlalchemy import select, text
from app.models.tenancy import Organization, Workspace
from app.models.profile import BusinessProfile
from app.models.suppression import SuppressionEntry
from app.models.leads import Company, Contact, ImportBatch
from app.core.rls import set_tenant_context


@pytest.mark.asyncio
async def test_phase1_rls_tenant_isolation(db_session):
    """
    Verifies that all Phase 1 business resource tables enforce strict tenant isolation.
    """
    bind = db_session.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # Setup 2 distinct workspaces
    org = Organization(name="Test Org RLS P1", slug=f"test-p1-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    await db_session.flush()

    ws_a = Workspace(organization_id=org.id, name="Workspace Alpha")
    ws_b = Workspace(organization_id=org.id, name="Workspace Beta")
    db_session.add_all([ws_a, ws_b])
    await db_session.flush()

    # Step 1: In Workspace A context, insert business profile, suppression entry, company, contact, import batch
    await set_tenant_context(db_session, ws_a.id)

    profile_a = BusinessProfile(
        workspace_id=ws_a.id,
        company_name="Alpha Corp",
        website_url="https://alpha.example.com",
        industry="SaaS",
        products_services=[{"name": "Alpha Cloud"}],
        value_propositions=["10x faster"],
        target_industries=["Tech"],
        ideal_customer_profiles=[{"tier": "Enterprise"}],
        disqualification_rules=["No budget"]
    )
    suppression_a = SuppressionEntry(
        workspace_id=ws_a.id,
        type="DOMAIN",
        value="blacklisted.com",
        reason="Competitor"
    )
    batch_a = ImportBatch(
        workspace_id=ws_a.id,
        filename="leads_a.csv",
        total_rows=10,
        valid_rows=8,
        duplicate_rows=1,
        suppressed_rows=1,
        error_rows=0
    )
    company_a = Company(
        workspace_id=ws_a.id,
        name="Target Corp",
        domain="target.com",
        normalized_domain="target.com",
        industry="Retail"
    )
    db_session.add_all([profile_a, suppression_a, batch_a, company_a])
    await db_session.flush()

    contact_a = Contact(
        workspace_id=ws_a.id,
        company_id=company_a.id,
        email="lead@target.com",
        first_name="Jane",
        last_name="Doe",
        title="VP Sales"
    )
    db_session.add(contact_a)
    await db_session.flush()

    # Verify Workspace A can query its own records
    result = await db_session.execute(select(Company).where(Company.workspace_id == ws_a.id))
    assert len(result.scalars().all()) == 1

    result = await db_session.execute(select(Contact).where(Contact.workspace_id == ws_a.id))
    assert len(result.scalars().all()) == 1

    result = await db_session.execute(select(BusinessProfile).where(BusinessProfile.workspace_id == ws_a.id))
    assert len(result.scalars().all()) == 1

    result = await db_session.execute(select(SuppressionEntry).where(SuppressionEntry.workspace_id == ws_a.id))
    assert len(result.scalars().all()) == 1

    # Step 2: Switch to Workspace B context
    if is_postgres:
        await set_tenant_context(db_session, ws_b.id)

        # In Workspace B, query all companies - must return 0 rows under RLS
        result = await db_session.execute(select(Company))
        assert len(result.scalars().all()) == 0

        # Query all contacts - must return 0 rows
        result = await db_session.execute(select(Contact))
        assert len(result.scalars().all()) == 0

        # Query all profiles - must return 0 rows
        result = await db_session.execute(select(BusinessProfile))
        assert len(result.scalars().all()) == 0

        # Query all suppression entries - must return 0 rows
        result = await db_session.execute(select(SuppressionEntry))
        assert len(result.scalars().all()) == 0

        # Query all batches - must return 0 rows
        result = await db_session.execute(select(ImportBatch))
        assert len(result.scalars().all()) == 0

        # Step 3: Verify missing context fails closed
        await db_session.execute(text("SELECT set_config('app.current_tenant_id', '', true)"))
        result = await db_session.execute(select(Company))
        assert len(result.scalars().all()) == 0
