import uuid
from typing import Optional
from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class SuppressionEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Workspace-scoped suppression entry for blacklisted domains or contact emails.
    Enforces tenant isolation via PostgreSQL RLS.
    """
    __tablename__ = "suppression_entries"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'DOMAIN' or 'EMAIL'
    value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint("workspace_id", "type", "value", name="uq_suppression_entry"),
    )
