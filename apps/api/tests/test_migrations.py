import os
from alembic.config import Config
from alembic.script import ScriptDirectory
from app.models.base import Base


def test_alembic_configuration_and_migration_discovery():
    """Verify that Alembic discovers migration 001_core_tenancy and verifies revision chain."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ini_path = os.path.join(base_dir, "alembic.ini")
    assert os.path.exists(ini_path)

    alembic_cfg = Config(ini_path)
    alembic_cfg.set_main_option("script_location", os.path.join(base_dir, "alembic"))
    script_dir = ScriptDirectory.from_config(alembic_cfg)

    revisions = list(script_dir.walk_revisions())
    assert len(revisions) >= 2
    head_rev = script_dir.get_current_head()
    assert head_rev == "002_lead_ingestion"


def test_schema_model_metadata_completeness():
    """Verify that all core tenancy and lead ingestion tables are registered in Base metadata."""
    expected_tables = {
        "organizations",
        "workspaces",
        "users",
        "workspace_memberships",
        "refresh_tokens",
        "audit_logs",
        "business_profiles",
        "suppression_entries",
        "import_batches",
        "companies",
        "contacts",
        "import_rows",
    }
    registered_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(registered_tables)

    # Check foreign keys on workspaces
    ws_table = Base.metadata.tables["workspaces"]
    fk_targets = {fk.target_fullname for fk in ws_table.foreign_keys}
    assert "organizations.id" in fk_targets

    # Check foreign keys on memberships
    membership_table = Base.metadata.tables["workspace_memberships"]
    m_fk_targets = {fk.target_fullname for fk in membership_table.foreign_keys}
    assert "workspaces.id" in m_fk_targets
    assert "users.id" in m_fk_targets
