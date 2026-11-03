"""001_core_tenancy

Revision ID: 001_core_tenancy
Revises: 
Create Date: 2026-10-20 16:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_core_tenancy'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Organizations Table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('billing_tier', sa.String(length=50), nullable=False, server_default='starter'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_organizations_slug', 'organizations', ['slug'], unique=True)

    # 2. Workspaces Table
    op.create_table(
        'workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_workspaces_organization_id', 'workspaces', ['organization_id'])

    # 3. Users Table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 4. Workspace Memberships Table
    workspace_role_enum = sa.Enum('OWNER', 'ADMIN', 'MEMBER', 'READ_ONLY', name='workspace_role')

    op.create_table(
        'workspace_memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', workspace_role_enum, nullable=False, server_default='MEMBER'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_membership')
    )
    op.create_index('ix_workspace_memberships_workspace_id', 'workspace_memberships', ['workspace_id'])
    op.create_index('ix_workspace_memberships_user_id', 'workspace_memberships', ['user_id'])

    # 5. Refresh Tokens Table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('family_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('replaced_by_hash', sa.String(length=64), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'], unique=True)
    op.create_index('ix_refresh_tokens_family_id', 'refresh_tokens', ['family_id'])
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])

    # 6. Audit Logs Table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_audit_logs_workspace_id', 'audit_logs', ['workspace_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])

    # 7. PostgreSQL Row-Level Security (RLS) Setup
    # RLS is enforced on tenant-owned data tables (audit_logs in Phase 0; leads/companies in Phase 1+).
    # Identity & tenancy control plane tables (orgs, workspaces, users, memberships, tokens)
    # are protected via application-level authentication & role checks.
    if is_postgres:
        op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;")
        op.execute("""
            CREATE POLICY audit_log_isolation_policy ON audit_logs
            FOR ALL
            USING (workspace_id IS NULL OR workspace_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
            WITH CHECK (workspace_id IS NULL OR workspace_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
        """)


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("DROP POLICY IF EXISTS audit_log_isolation_policy ON audit_logs;")

    op.drop_table('audit_logs')
    op.drop_table('refresh_tokens')
    op.drop_table('workspace_memberships')
    
    workspace_role_enum = sa.Enum('OWNER', 'ADMIN', 'MEMBER', 'READ_ONLY', name='workspace_role')
    workspace_role_enum.drop(bind, checkfirst=True)

    op.drop_table('users')
    op.drop_table('workspaces')
    op.drop_table('organizations')
