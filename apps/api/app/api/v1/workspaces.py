from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.api.deps import TenantContext, get_current_tenant_context, require_role
from app.models.audit import AuditLog
from app.models.tenancy import WorkspaceRole
from app.schemas.tenancy import WorkspaceRead

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


class WorkspaceUpdateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)


class AuditLogRead(BaseModel):
    id: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    created_at: str


@router.get("/current", response_model=WorkspaceRead)
async def get_current_workspace(
    context: TenantContext = Depends(get_current_tenant_context)
):
    """
    Returns the active workspace.
    Demonstrates validated server-side workspace context and PostgreSQL RLS binding.
    """
    return WorkspaceRead(
        id=context.workspace.id,
        organization_id=context.workspace.organization_id,
        name=context.workspace.name,
        is_active=context.workspace.is_active,
        role=context.role.value,
        created_at=context.workspace.created_at
    )


@router.patch("/current", response_model=WorkspaceRead)
async def update_current_workspace(
    payload: WorkspaceUpdateRequest,
    context: TenantContext = Depends(require_role(WorkspaceRole.ADMIN))
):
    """
    Updates current workspace attributes.
    Demonstrates RBAC enforcement: requires minimum ADMIN role.
    """
    ws_read = WorkspaceRead(
        id=context.workspace.id,
        organization_id=context.workspace.organization_id,
        name=payload.name,
        is_active=context.workspace.is_active,
        role=context.role.value,
        created_at=context.workspace.created_at
    )

    context.workspace.name = payload.name
    
    audit = AuditLog(
        workspace_id=context.workspace.id,
        user_id=context.user.id,
        action="WORKSPACE_UPDATE",
        resource_type="workspace",
        resource_id=str(context.workspace.id),
        details={"new_name": payload.name}
    )
    context.session.add(audit)
    await context.session.commit()

    return ws_read


@router.get("/current/audit-logs")
async def get_workspace_audit_logs(
    context: TenantContext = Depends(get_current_tenant_context)
):
    """
    Returns audit logs for the current workspace.
    Demonstrates PostgreSQL RLS: query returns ONLY records matching app.current_tenant_id.
    """
    query = (
        select(AuditLog)
        .where(AuditLog.workspace_id == context.workspace.id)
        .order_by(AuditLog.created_at.desc())
        .limit(50)
    )
    result = await context.session.execute(query)
    logs = result.scalars().all()
    
    return [
        {
            "id": str(log.id),
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "created_at": log.created_at.isoformat()
        }
        for log in logs
    ]
