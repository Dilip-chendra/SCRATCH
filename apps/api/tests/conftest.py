import os
import sys
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure apps/api is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.deps import get_db
from app.core.database import get_db_session
from app.core.security import hash_password
from app.main import app
from app.models.base import Base
from app.models.tenancy import Organization, User, Workspace, WorkspaceMembership, WorkspaceRole

# Use an in-memory SQLite database for fast, isolated async testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Provides a fresh database session with all tables created in-memory."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    """Provides an authenticated HTTP test client wired to the test database session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_session] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seed_data(db_session: AsyncSession):
    """Seeds two isolated organizations, workspaces, and users for multi-tenant testing."""
    user_a_id = uuid.uuid4()
    org_a_id = uuid.uuid4()
    ws_a_id = uuid.uuid4()
    membership_a_id = uuid.uuid4()

    user_a = User(
        id=user_a_id,
        email="user_a@company-a.com",
        hashed_password=hash_password("Password123!"),
        full_name="Alice User A",
        is_active=True
    )
    org_a = Organization(
        id=org_a_id,
        name="Company A Org",
        slug="company-a",
        billing_tier="starter"
    )
    ws_a = Workspace(
        id=ws_a_id,
        organization_id=org_a_id,
        name="Workspace A",
        is_active=True
    )
    membership_a = WorkspaceMembership(
        id=membership_a_id,
        workspace_id=ws_a_id,
        user_id=user_a_id,
        role=WorkspaceRole.OWNER,
        is_active=True
    )

    user_b_id = uuid.uuid4()
    org_b_id = uuid.uuid4()
    ws_b_id = uuid.uuid4()
    membership_b_id = uuid.uuid4()

    user_b = User(
        id=user_b_id,
        email="user_b@company-b.com",
        hashed_password=hash_password("Password123!"),
        full_name="Bob User B",
        is_active=True
    )
    org_b = Organization(
        id=org_b_id,
        name="Company B Org",
        slug="company-b",
        billing_tier="starter"
    )
    ws_b = Workspace(
        id=ws_b_id,
        organization_id=org_b_id,
        name="Workspace B",
        is_active=True
    )
    membership_b = WorkspaceMembership(
        id=membership_b_id,
        workspace_id=ws_b_id,
        user_id=user_b_id,
        role=WorkspaceRole.MEMBER,
        is_active=True
    )

    db_session.add_all([user_a, org_a, ws_a, membership_a, user_b, org_b, ws_b, membership_b])
    await db_session.commit()

    # Expire objects are refreshed or returned with explicit detached properties
    return {
        "user_a_id": user_a_id,
        "ws_a_id": ws_a_id,
        "org_a_id": org_a_id,
        "user_b_id": user_b_id,
        "ws_b_id": ws_b_id,
        "org_b_id": org_b_id,
        "user_a": user_a,
        "ws_a": ws_a,
        "user_b": user_b,
        "ws_b": ws_b,
    }
