import uuid
from typing import Optional, Tuple, List
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.suppression import SuppressionEntry
from app.services.normalization import normalize_domain, normalize_email


async def check_is_suppressed(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    normalized_domain: Optional[str] = None,
    normalized_email: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Checks if a normalized domain or email is in the workspace's suppression list.
    Returns (is_suppressed, reason).
    """
    conditions = []
    if normalized_domain:
        conditions.append(
            (SuppressionEntry.type == "DOMAIN") & (SuppressionEntry.value == normalized_domain)
        )
    if normalized_email:
        conditions.append(
            (SuppressionEntry.type == "EMAIL") & (SuppressionEntry.value == normalized_email)
        )

    if not conditions:
        return False, None

    from sqlalchemy import or_
    stmt = (
        select(SuppressionEntry)
        .where(
            SuppressionEntry.workspace_id == workspace_id,
            or_(*conditions)
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()

    if entry:
        return True, entry.reason or f"Suppressed by {entry.type} list ({entry.value})"
    return False, None


async def add_suppression_entry(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    entry_type: str,
    raw_value: str,
    reason: Optional[str] = None,
) -> SuppressionEntry:
    """
    Adds a new suppression entry with canonical normalization.
    """
    clean_type = entry_type.strip().upper()
    if clean_type not in ("DOMAIN", "EMAIL"):
        raise ValueError("Suppression entry type must be 'DOMAIN' or 'EMAIL'")

    if clean_type == "DOMAIN":
        canonical_value = normalize_domain(raw_value)
        if not canonical_value:
            raise ValueError(f"Invalid domain value: '{raw_value}'")
    else:
        canonical_value = normalize_email(raw_value)
        if not canonical_value:
            raise ValueError(f"Invalid email value: '{raw_value}'")

    # Check if already exists
    stmt = select(SuppressionEntry).where(
        SuppressionEntry.workspace_id == workspace_id,
        SuppressionEntry.type == clean_type,
        SuppressionEntry.value == canonical_value,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        if reason and existing.reason != reason:
            existing.reason = reason
            await db.flush()
        return existing

    entry = SuppressionEntry(
        workspace_id=workspace_id,
        type=clean_type,
        value=canonical_value,
        reason=reason,
    )
    db.add(entry)
    await db.flush()
    return entry


async def list_suppression_entries(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    limit: int = 100,
    offset: int = 0,
) -> List[SuppressionEntry]:
    """Lists suppression entries for a workspace."""
    stmt = (
        select(SuppressionEntry)
        .where(SuppressionEntry.workspace_id == workspace_id)
        .order_by(SuppressionEntry.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def delete_suppression_entry(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    entry_id: uuid.UUID,
) -> bool:
    """Deletes a suppression entry by ID."""
    stmt = delete(SuppressionEntry).where(
        SuppressionEntry.workspace_id == workspace_id,
        SuppressionEntry.id == entry_id,
    )
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount > 0
