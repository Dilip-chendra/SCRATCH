from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_tenant_context(session: AsyncSession, workspace_id: UUID | str) -> None:
    """
    Sets the transaction-local tenant context using PostgreSQL's set_config with parameter binding.
    The third parameter `true` sets is_local = true, guaranteeing the setting resets on transaction end.
    """
    bind = session.get_bind()
    dialect_name = bind.dialect.name if bind else ""
    
    if dialect_name == "postgresql":
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :ws_id, true)"),
            {"ws_id": str(workspace_id)}
        )


@asynccontextmanager
async def tenant_transaction(
    session: AsyncSession, workspace_id: UUID | str
) -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager guaranteeing that tenant context is established inside
    an explicit transaction alongside protected queries.
    When the transaction commits or rolls back, PostgreSQL automatically resets
    the transaction-local setting, preventing pool contamination.
    """
    # If the session does not already have an active transaction, start one
    if not session.in_transaction():
        async with session.begin():
            await set_tenant_context(session, workspace_id)
            yield session
    else:
        await set_tenant_context(session, workspace_id)
        yield session
