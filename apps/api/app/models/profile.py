import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy import String, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class BusinessProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Workspace-scoped business profile configuring products, value propositions,
    target industries, ICP profiles, and disqualification rules.
    Enforces tenant isolation via PostgreSQL RLS.
    """
    __tablename__ = "business_profiles"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    website_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Structured ICP and positioning definitions
    products_services: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    value_propositions: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    target_industries: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    ideal_customer_profiles: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    disqualification_rules: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
