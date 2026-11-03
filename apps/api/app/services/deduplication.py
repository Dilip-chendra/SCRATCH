import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.leads import Company, Contact


async def find_existing_company(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    normalized_domain: str
) -> Optional[Company]:
    """Finds an existing company in the workspace by canonical domain."""
    if not normalized_domain:
        return None

    stmt = select(Company).where(
        Company.workspace_id == workspace_id,
        Company.normalized_domain == normalized_domain
    ).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def find_existing_contact(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    normalized_email: str
) -> Optional[Contact]:
    """Finds an existing contact in the workspace by normalized email."""
    if not normalized_email:
        return None

    stmt = select(Contact).where(
        Contact.workspace_id == workspace_id,
        Contact.email == normalized_email
    ).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
