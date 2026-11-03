import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class BusinessProfileBase(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    website_url: Optional[str] = Field(None, max_length=500)
    industry: Optional[str] = Field(None, max_length=100)
    products_services: List[Dict[str, Any]] = Field(default_factory=list)
    value_propositions: List[str] = Field(default_factory=list)
    target_industries: List[str] = Field(default_factory=list)
    ideal_customer_profiles: List[Dict[str, Any]] = Field(default_factory=list)
    disqualification_rules: List[str] = Field(default_factory=list)


class BusinessProfileUpdate(BusinessProfileBase):
    pass


class BusinessProfileResponse(BusinessProfileBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
