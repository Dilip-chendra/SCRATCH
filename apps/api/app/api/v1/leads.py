import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select, or_
from app.api.deps import TenantContext, get_current_tenant_context, require_role
from app.models.tenancy import WorkspaceRole
from app.models.leads import ImportBatch, ImportRow, Company, Contact
from app.schemas.leads import (
    UploadPreviewResponse,
    ImportBatchResponse,
    ImportRowResponse,
    CompanyResponse,
    ContactResponse,
)
from app.services.ingestion import detect_columns_and_preview, execute_lead_import

router = APIRouter(prefix="/leads", tags=["Leads & Ingestion"])


@router.post("/upload", response_model=UploadPreviewResponse)
async def preview_lead_file(
    file: UploadFile = File(...),
    context: TenantContext = Depends(require_role(WorkspaceRole.MEMBER))
):
    """
    Analyzes an uploaded CSV or tabular file.
    Detects delimiters, suggests auto-mapped canonical columns, and returns preview rows.
    """
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty"
        )

    try:
        preview = detect_columns_and_preview(content, file.filename or "leads.csv")
        return preview
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse file: {str(exc)}"
        )


@router.post("/import", response_model=ImportBatchResponse)
async def import_leads(
    file: UploadFile = File(...),
    column_mapping: str = Form(...),
    context: TenantContext = Depends(require_role(WorkspaceRole.MEMBER))
):
    """
    Executes streaming lead ingestion with confirmed column mappings.
    Normalizes domains/emails, suppresses blacklisted entities, and deduplicates against workspace data.
    """
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Import file is empty"
        )

    try:
        mapping_dict = json.loads(column_mapping)
        if not isinstance(mapping_dict, dict):
            raise ValueError()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="column_mapping must be a valid JSON object"
        )

    result = await execute_lead_import(
        db=context.session,
        workspace_id=context.workspace.id,
        filename=file.filename or "leads.csv",
        file_content=content,
        column_mapping=mapping_dict,
    )
    return result


@router.get("/batches", response_model=List[ImportBatchResponse])
async def list_import_batches(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    context: TenantContext = Depends(get_current_tenant_context)
):
    """Lists recent import batches for the workspace."""
    stmt = (
        select(ImportBatch)
        .where(ImportBatch.workspace_id == context.workspace.id)
        .order_by(ImportBatch.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await context.session.execute(stmt)
    batches = result.scalars().all()
    return [
        ImportBatchResponse(
            batch_id=b.id,
            filename=b.filename,
            total_rows=b.total_rows,
            valid_rows=b.valid_rows,
            duplicate_rows=b.duplicate_rows,
            suppressed_rows=b.suppressed_rows,
            error_rows=b.error_rows,
            status=b.status,
            created_at=b.created_at,
        )
        for b in batches
    ]


@router.get("/batches/{batch_id}", response_model=ImportBatchResponse)
async def get_import_batch(
    batch_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context)
):
    """Retrieves metadata and counters for a specific import batch."""
    stmt = select(ImportBatch).where(
        ImportBatch.workspace_id == context.workspace.id,
        ImportBatch.id == batch_id
    )
    result = await context.session.execute(stmt)
    b = result.scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    return ImportBatchResponse(
        batch_id=b.id,
        filename=b.filename,
        total_rows=b.total_rows,
        valid_rows=b.valid_rows,
        duplicate_rows=b.duplicate_rows,
        suppressed_rows=b.suppressed_rows,
        error_rows=b.error_rows,
        status=b.status,
        created_at=b.created_at,
    )


@router.get("/batches/{batch_id}/rows", response_model=List[ImportRowResponse])
async def get_batch_rows(
    batch_id: uuid.UUID,
    status_filter: Optional[str] = Query(None, regex="^(VALID|DUPLICATE|SUPPRESSED|ERROR)$"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    context: TenantContext = Depends(get_current_tenant_context)
):
    """Retrieves row-level tracking and quarantine data for a batch."""
    stmt = (
        select(ImportRow)
        .where(
            ImportRow.workspace_id == context.workspace.id,
            ImportRow.batch_id == batch_id,
        )
    )
    if status_filter:
        stmt = stmt.where(ImportRow.status == status_filter)

    stmt = stmt.order_by(ImportRow.row_number.asc()).limit(limit).offset(offset)
    result = await context.session.execute(stmt)
    return list(result.scalars().all())


@router.get("/companies", response_model=List[CompanyResponse])
async def list_companies(
    query: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    context: TenantContext = Depends(get_current_tenant_context)
):
    """Lists imported accounts/companies with search filtering."""
    stmt = (
        select(Company)
        .where(Company.workspace_id == context.workspace.id)
    )
    if query:
        q_clean = f"%{query.strip().lower()}%"
        stmt = stmt.where(
            or_(
                Company.name.ilike(q_clean),
                Company.normalized_domain.ilike(q_clean),
                Company.industry.ilike(q_clean)
            )
        )

    stmt = stmt.order_by(Company.name.asc()).limit(limit).offset(offset)
    result = await context.session.execute(stmt)
    return list(result.scalars().all())


@router.get("/contacts", response_model=List[ContactResponse])
async def list_contacts(
    query: Optional[str] = Query(None),
    company_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    context: TenantContext = Depends(get_current_tenant_context)
):
    """Lists imported contacts with search and company filtering."""
    stmt = (
        select(Contact)
        .where(Contact.workspace_id == context.workspace.id)
    )
    if company_id:
        stmt = stmt.where(Contact.company_id == company_id)

    if query:
        q_clean = f"%{query.strip().lower()}%"
        stmt = stmt.where(
            or_(
                Contact.email.ilike(q_clean),
                Contact.first_name.ilike(q_clean),
                Contact.last_name.ilike(q_clean),
                Contact.title.ilike(q_clean)
            )
        )

    stmt = stmt.order_by(Contact.created_at.desc()).limit(limit).offset(offset)
    result = await context.session.execute(stmt)
    return list(result.scalars().all())
