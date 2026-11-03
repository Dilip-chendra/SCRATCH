import uuid
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class ImportBatch(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks a lead ingestion batch, recording metrics for valid, duplicate,
    suppressed, and quarantined rows.
    """
    __tablename__ = "import_batches"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suppressed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="COMPLETED")  # PENDING, PROCESSING, COMPLETED, FAILED


class ImportRow(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Row-level ingestion tracking and quarantine table.
    Enforces tenant isolation via PostgreSQL RLS.
    """
    __tablename__ = "import_rows"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # VALID, DUPLICATE, SUPPRESSED, ERROR
    error_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)


class Company(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Workspace-scoped company / account entity with canonical normalized domain deduplication.
    Enforces tenant isolation via PostgreSQL RLS.
    """
    __tablename__ = "companies"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    employee_count_range: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")
    custom_attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("workspace_id", "normalized_domain", name="uq_companies_workspace_domain"),
    )


class Contact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Workspace-scoped contact entity with email deduplication and company relationship.
    Enforces tenant isolation via PostgreSQL RLS.
    """
    __tablename__ = "contacts"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")
    custom_attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("workspace_id", "email", name="uq_contacts_workspace_email"),
    )
