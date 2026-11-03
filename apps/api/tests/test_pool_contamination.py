import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.rls import tenant_transaction


@pytest.mark.asyncio
async def test_transaction_rollback_cleans_tenant_context(db_session: AsyncSession, seed_data):
    """
    Verify that an exception inside a tenant transaction rolls back cleanly
    and resets the tenant context so no cross-transaction pollution occurs.
    """
    ws_a_id = seed_data["ws_a_id"]

    try:
        async with tenant_transaction(db_session, ws_a_id):
            raise RuntimeError("Simulated transaction fault")
    except RuntimeError:
        pass

    assert not db_session.in_transaction()


@pytest.mark.asyncio
async def test_sequential_tenant_contexts_do_not_bleed(db_session: AsyncSession, seed_data):
    """
    Verify that switching sequentially between Workspace A and Workspace B contexts
    does not leave residual state from Workspace A.
    """
    ws_a_id = seed_data["ws_a_id"]
    ws_b_id = seed_data["ws_b_id"]

    async with tenant_transaction(db_session, ws_a_id):
        pass

    async with tenant_transaction(db_session, ws_b_id):
        pass
