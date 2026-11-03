from dataclasses import dataclass
from typing import AsyncGenerator, Optional
from uuid import UUID
from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.core.rls import set_tenant_context
from app.core.security import decode_access_token
from app.models.tenancy import User, Workspace, WorkspaceMembership, WorkspaceRole


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    request: Request,
    access_token_cookie: Optional[str] = Cookie(None, alias="access_token"),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Authenticates the user from an HttpOnly cookie or an Authorization Bearer header.
    Validates token signature, non-expiration, and active user state in the database.
    """
    token: Optional[str] = None
    if access_token_cookie:
        token = access_token_cookie
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ")[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        user_id = UUID(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed user identifier in token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


@dataclass
class TenantContext:
    user: User
    workspace: Workspace
    role: WorkspaceRole
    session: AsyncSession


async def get_current_tenant_context(
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> AsyncGenerator[TenantContext, None]:
    """
    Validates that the authenticated user has active membership in the requested workspace,
    establishes transaction-scoped PostgreSQL RLS tenant context via set_config, and
    yields a TenantContext.
    """
    if not x_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Workspace-ID header is required for tenant-scoped operations"
        )

    try:
        workspace_uuid = UUID(x_workspace_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Workspace-ID header format; must be a valid UUID"
        )

    # 1. Server-side validation of workspace membership & active role
    query = (
        select(WorkspaceMembership, Workspace)
        .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
        .where(
            WorkspaceMembership.user_id == current_user.id,
            WorkspaceMembership.workspace_id == workspace_uuid,
            WorkspaceMembership.is_active.is_(True),
            Workspace.is_active.is_(True)
        )
    )
    result = await db.execute(query)
    record = result.first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have active membership in the specified workspace"
        )

    membership, workspace = record

    # 2. Establish transaction-scoped PostgreSQL RLS context
    if not db.in_transaction():
        await db.begin()

    await set_tenant_context(db, workspace.id)

    try:
        yield TenantContext(
            user=current_user,
            workspace=workspace,
            role=membership.role,
            session=db
        )
        if db.in_transaction():
            await db.commit()
    except Exception:
        if db.in_transaction():
            await db.rollback()
        raise


def require_role(min_role: WorkspaceRole):
    """Factory dependency to enforce minimum RBAC role hierarchy."""
    role_weights = {
        WorkspaceRole.READ_ONLY: 1,
        WorkspaceRole.MEMBER: 2,
        WorkspaceRole.ADMIN: 3,
        WorkspaceRole.OWNER: 4,
    }

    async def role_checker(
        context: TenantContext = Depends(get_current_tenant_context)
    ) -> TenantContext:
        user_weight = role_weights.get(context.role, 0)
        required_weight = role_weights.get(min_role, 99)

        if user_weight < required_weight:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires minimum '{min_role.value}' role; user has '{context.role.value}'"
            )
        return context

    return role_checker
