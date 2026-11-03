import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SuppressionCreate(BaseModel):
    type: str = Field(..., pattern="^(DOMAIN|EMAIL)$")
    value: str = Field(..., min_length=1, max_length=255)
    reason: Optional[str] = Field(None, max_length=255)


class SuppressionResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    type: str
    value: str
    reason: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
