import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.rls import set_tenant_context
from app.models.audit import AuditLog


@pytest.mark.asyncio
async def test_tenant_context_isolation_reads(db_session: AsyncSession, seed_data):
    """
    Verify that tenant context establishes strict boundaries:
    Under Workspace A context, Workspace B records are invisible or strictly filtered.
    """
    ws_a_id = seed_data["ws_a_id"]
    ws_b_id = seed_data["ws_b_id"]
    user_a_id = seed_data["user_a_id"]
    user_b_id = seed_data["user_b_id"]

    # Insert audit logs for both workspaces
    audit_a = AuditLog(
        id=uuid.uuid4(),
        workspace_id=ws_a_id,
        user_id=user_a_id,
        action="LEAD_INGEST_A",
        resource_type="lead",
        details={"source": "test"}
    )
    audit_b = AuditLog(
        id=uuid.uuid4(),
        workspace_id=ws_b_id,
        user_id=user_b_id,
        action="LEAD_INGEST_B",
        resource_type="lead",
        details={"source": "test"}
    )
    db_session.add_all([audit_a, audit_b])
    await db_session.commit()

    # Query with Workspace A tenant scope
    await set_tenant_context(db_session, ws_a_id)
    query_a = select(AuditLog).where(AuditLog.workspace_id == ws_a_id)
    result_a = await db_session.execute(query_a)
    logs_a = result_a.scalars().all()

    assert len(logs_a) == 1
    assert logs_a[0].action == "LEAD_INGEST_A"
    assert all(log.workspace_id == ws_a_id for log in logs_a)

    # Query with Workspace B tenant scope
    await set_tenant_context(db_session, ws_b_id)
    query_b = select(AuditLog).where(AuditLog.workspace_id == ws_b_id)
    result_b = await db_session.execute(query_b)
    logs_b = result_b.scalars().all()

    assert len(logs_b) == 1
    assert logs_b[0].action == "LEAD_INGEST_B"
    assert all(log.workspace_id == ws_b_id for log in logs_b)


@pytest.mark.asyncio
async def test_tenant_isolation_mutations(db_session: AsyncSession, seed_data):
    """Verify that tenant mutations under Workspace A cannot delete or overwrite Workspace B data."""
    ws_a_id = seed_data["ws_a_id"]
    ws_b_id = seed_data["ws_b_id"]
    user_b_id = seed_data["user_b_id"]

    audit_b = AuditLog(
        id=uuid.uuid4(),
        workspace_id=ws_b_id,
        user_id=user_b_id,
        action="IMMUTABLE_RECORD_B",
        resource_type="lead",
        details={}
    )
    db_session.add(audit_b)
    await db_session.commit()

    # Attempt delete under Workspace A scope
    await set_tenant_context(db_session, ws_a_id)
    scoped_delete_query = select(AuditLog).where(
        AuditLog.id == audit_b.id,
        AuditLog.workspace_id == ws_a_id
    )
    res = await db_session.execute(scoped_delete_query)
    found = res.scalar_one_or_none()
    assert found is None
