import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.api.deps import TenantContext, get_current_tenant_context, require_role
from app.models.tenancy import WorkspaceRole
from app.schemas.suppression import SuppressionCreate, SuppressionResponse
from app.services.suppression import (
    add_suppression_entry,
    list_suppression_entries,
    delete_suppression_entry,
)

router = APIRouter(prefix="/suppression", tags=["Suppression"])


@router.get("", response_model=List[SuppressionResponse])
async def get_suppression_list(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    context: TenantContext = Depends(get_current_tenant_context)
):
    """Lists all suppression entries for the current workspace."""
    return await list_suppression_entries(
        context.session,
        workspace_id=context.workspace.id,
        limit=limit,
        offset=offset
    )


@router.post("", response_model=SuppressionResponse, status_code=status.HTTP_201_CREATED)
async def create_suppression_entry(
    payload: SuppressionCreate,
    context: TenantContext = Depends(require_role(WorkspaceRole.MEMBER))
):
    """
    Adds a new suppressed domain or email address.
    Requires minimum MEMBER role.
    """
    try:
        entry = await add_suppression_entry(
            context.session,
            workspace_id=context.workspace.id,
            entry_type=payload.type,
            raw_value=payload.value,
            reason=payload.reason
        )
        return entry
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_suppression_entry(
    entry_id: uuid.UUID,
    context: TenantContext = Depends(require_role(WorkspaceRole.MEMBER))
):
    """Deletes a suppression entry by ID."""
    deleted = await delete_suppression_entry(
        context.session,
        workspace_id=context.workspace.id,
        entry_id=entry_id
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suppression entry not found"
        )
    return None
