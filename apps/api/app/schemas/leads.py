import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class UploadPreviewResponse(BaseModel):
    filename: str
    delimiter: str
    headers: List[str]
    suggested_mappings: Dict[str, str]
    sample_rows: List[Dict[str, str]]
    total_estimated_rows: int


class ImportCommitRequest(BaseModel):
    filename: str
    file_content_base64: Optional[str] = None
    column_mapping: Dict[str, str]


class ImportBatchResponse(BaseModel):
    batch_id: uuid.UUID
    filename: str
    total_rows: int
    valid_rows: int
    duplicate_rows: int
    suppressed_rows: int
    error_rows: int
    status: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ImportRowResponse(BaseModel):
    id: uuid.UUID
    row_number: int
    status: str
    raw_data: Dict[str, Any]
    error_details: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    domain: str
    normalized_domain: str
    industry: Optional[str] = None
    employee_count_range: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContactResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    company_id: Optional[uuid.UUID] = None
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
