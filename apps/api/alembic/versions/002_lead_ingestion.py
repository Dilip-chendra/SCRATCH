"""002_lead_ingestion

Revision ID: 002_lead_ingestion
Revises: 001_core_tenancy
Create Date: 2026-10-20 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_lead_ingestion'
down_revision: Union[str, None] = '001_core_tenancy'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Business Profiles Table
    op.create_table(
        'business_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('website_url', sa.String(length=500), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('products_services', sa.JSON(), nullable=False),
        sa.Column('value_propositions', sa.JSON(), nullable=False),
        sa.Column('target_industries', sa.JSON(), nullable=False),
        sa.Column('ideal_customer_profiles', sa.JSON(), nullable=False),
        sa.Column('disqualification_rules', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('workspace_id', name='uq_business_profiles_workspace')
    )
    op.create_index('ix_business_profiles_workspace_id', 'business_profiles', ['workspace_id'])

    # 2. Suppression Entries Table
    op.create_table(
        'suppression_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('workspace_id', 'type', 'value', name='uq_suppression_entry')
    )
    op.create_index('ix_suppression_entries_workspace_id', 'suppression_entries', ['workspace_id'])
    op.create_index('ix_suppression_entries_value', 'suppression_entries', ['value'])

    # 3. Import Batches Table
    op.create_table(
        'import_batches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('total_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('valid_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duplicate_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('suppressed_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='COMPLETED'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_import_batches_workspace_id', 'import_batches', ['workspace_id'])

    # 4. Companies Table
    op.create_table(
        'companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=False),
        sa.Column('normalized_domain', sa.String(length=255), nullable=False),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('employee_count_range', sa.String(length=50), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('custom_attributes', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('workspace_id', 'normalized_domain', name='uq_companies_workspace_domain')
    )
    op.create_index('ix_companies_workspace_id', 'companies', ['workspace_id'])
    op.create_index('ix_companies_name', 'companies', ['name'])
    op.create_index('ix_companies_normalized_domain', 'companies', ['normalized_domain'])

    # 5. Contacts Table
    op.create_table(
        'contacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id', ondelete='SET NULL'), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('title', sa.String(length=150), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('linkedin_url', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('custom_attributes', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('workspace_id', 'email', name='uq_contacts_workspace_email')
    )
    op.create_index('ix_contacts_workspace_id', 'contacts', ['workspace_id'])
    op.create_index('ix_contacts_company_id', 'contacts', ['company_id'])
    op.create_index('ix_contacts_email', 'contacts', ['email'])

    # 6. Import Rows Table
    op.create_table(
        'import_rows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('import_batches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('row_number', sa.Integer(), nullable=False),
        sa.Column('raw_data', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_import_rows_workspace_id', 'import_rows', ['workspace_id'])
    op.create_index('ix_import_rows_batch_id', 'import_rows', ['batch_id'])

    # 7. PostgreSQL Row-Level Security (RLS) Setup for Phase 1 Tenant Tables
    tables_for_rls = [
        ('business_profiles', 'business_profile_isolation_policy'),
        ('suppression_entries', 'suppression_entry_isolation_policy'),
        ('import_batches', 'import_batch_isolation_policy'),
        ('companies', 'company_isolation_policy'),
        ('contacts', 'contact_isolation_policy'),
        ('import_rows', 'import_row_isolation_policy'),
    ]

    if is_postgres:
        for tbl, policy_name in tables_for_rls:
            op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;")
            op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;")
            op.execute(f"""
                CREATE POLICY {policy_name} ON {tbl}
                FOR ALL
                USING (workspace_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
                WITH CHECK (workspace_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
            """)


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    tables_for_rls = [
        ('import_rows', 'import_row_isolation_policy'),
        ('contacts', 'contact_isolation_policy'),
        ('companies', 'company_isolation_policy'),
        ('import_batches', 'import_batch_isolation_policy'),
        ('suppression_entries', 'suppression_entry_isolation_policy'),
        ('business_profiles', 'business_profile_isolation_policy'),
    ]

    if is_postgres:
        for tbl, policy_name in tables_for_rls:
            op.execute(f"DROP POLICY IF EXISTS {policy_name} ON {tbl};")

    op.drop_table('import_rows')
    op.drop_table('contacts')
    op.drop_table('companies')
    op.drop_table('import_batches')
    op.drop_table('suppression_entries')
    op.drop_table('business_profiles')
