from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.schemas.tenancy import WorkspaceRead


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    full_name: str = Field(..., min_length=2)
    organization_name: Optional[str] = None
    workspace_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_superuser: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    csrf_token: str
    user: UserRead
    workspaces: List[WorkspaceRead]


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    csrf_token: str
