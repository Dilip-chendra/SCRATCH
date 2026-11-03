import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_csrf_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password
)
from app.models.audit import AuditLog
from app.models.auth import RefreshToken
from app.models.tenancy import Organization, User, Workspace, WorkspaceMembership, WorkspaceRole
from app.schemas.auth import LoginRequest, RefreshResponse, RegisterRequest, TokenResponse, UserRead
from app.schemas.tenancy import WorkspaceRead

router = APIRouter(prefix="/auth", tags=["Authentication"])


def set_auth_cookies(response: Response, access_token: str, refresh_token: str, csrf_token: str) -> None:
    """Sets secure HttpOnly cookies for access/refresh tokens and non-HttpOnly for CSRF token."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/api/v1/auth"
    )
    # Non-HttpOnly CSRF token readable by client to populate X-CSRF-Token header
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/"
    )


def clear_auth_cookies(response: Response) -> None:
    """Clears all authentication and CSRF cookies upon logout."""
    response.delete_cookie(key="access_token", path="/", domain=settings.COOKIE_DOMAIN)
    response.delete_cookie(key="refresh_token", path="/api/v1/auth", domain=settings.COOKIE_DOMAIN)
    response.delete_cookie(key="csrf_token", path="/", domain=settings.COOKIE_DOMAIN)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Registers a new user, creates their root Organization and default Workspace,
    and assigns them as OWNER.
    """
    existing_user = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists"
        )

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        is_active=True
    )
    db.add(user)
    await db.flush()

    org_name = payload.organization_name or f"{payload.full_name}'s Organization"
    base_slug = org_name.lower().replace(" ", "-")[:50]
    unique_slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
    organization = Organization(
        name=org_name,
        slug=unique_slug,
        billing_tier="starter"
    )
    db.add(organization)
    await db.flush()

    ws_name = payload.workspace_name or "Default Workspace"
    workspace = Workspace(
        organization_id=organization.id,
        name=ws_name,
        is_active=True
    )
    db.add(workspace)
    await db.flush()

    membership = WorkspaceMembership(
        workspace_id=workspace.id,
        user_id=user.id,
        role=WorkspaceRole.OWNER,
        is_active=True
    )
    db.add(membership)

    family_id = uuid.uuid4()
    raw_refresh_token, token_hash = generate_refresh_token()
    refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        family_id=family_id,
        is_revoked=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(refresh_record)

    user_id = user.id
    user_email = user.email
    user_full_name = user.full_name
    user_is_active = user.is_active
    user_is_superuser = user.is_superuser
    user_created_at = user.created_at

    ws_id = workspace.id
    ws_org_id = workspace.organization_id
    ws_name = workspace.name
    ws_is_active = workspace.is_active
    ws_created_at = workspace.created_at

    audit = AuditLog(
        workspace_id=None,
        user_id=user_id,
        action="AUTH_REGISTER",
        resource_type="user",
        resource_id=str(user_id),
        details={"email": user_email, "organization_id": str(organization.id), "workspace_id": str(ws_id)},
        ip_address=request.client.host if request.client else None
    )
    db.add(audit)
    await db.commit()

    user_read = UserRead(
        id=user_id,
        email=user_email,
        full_name=user_full_name,
        is_active=user_is_active,
        is_superuser=user_is_superuser,
        created_at=user_created_at
    )
    ws_read = WorkspaceRead(
        id=ws_id,
        organization_id=ws_org_id,
        name=ws_name,
        is_active=ws_is_active,
        role=WorkspaceRole.OWNER.value,
        created_at=ws_created_at
    )

    access_token = create_access_token(
        subject=str(user_id),
        extra_claims={"email": user_email}
    )
    csrf_token = generate_csrf_token(str(user_id))
    set_auth_cookies(response, access_token, raw_refresh_token, csrf_token)

    return TokenResponse(
        access_token=access_token,
        expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        csrf_token=csrf_token,
        user=user_read,
        workspaces=[ws_read]
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticates user credentials using Argon2id, generates tokens, and sets cookies.
    """
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled"
        )

    # Fetch user's workspaces
    ws_query = (
        select(Workspace, WorkspaceMembership.role)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
        .where(
            WorkspaceMembership.user_id == user.id,
            WorkspaceMembership.is_active.is_(True),
            Workspace.is_active.is_(True)
        )
    )
    ws_results = await db.execute(ws_query)
    workspaces: List[WorkspaceRead] = []
    first_workspace_id = None
    for ws, role in ws_results.all():
        if not first_workspace_id:
            first_workspace_id = ws.id
        workspaces.append(
            WorkspaceRead(
                id=ws.id,
                organization_id=ws.organization_id,
                name=ws.name,
                is_active=ws.is_active,
                role=role.value,
                created_at=ws.created_at
            )
        )

    family_id = uuid.uuid4()
    raw_refresh_token, token_hash = generate_refresh_token()
    refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        family_id=family_id,
        is_revoked=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(refresh_record)

    user_id = user.id
    user_email = user.email
    user_full_name = user.full_name
    user_is_active = user.is_active
    user_is_superuser = user.is_superuser
    user_created_at = user.created_at

    audit = AuditLog(
        workspace_id=None,
        user_id=user_id,
        action="AUTH_LOGIN",
        resource_type="user",
        resource_id=str(user_id),
        details={"email": user_email, "default_workspace_id": str(first_workspace_id) if first_workspace_id else None},
        ip_address=request.client.host if request.client else None
    )
    db.add(audit)
    await db.commit()

    user_read = UserRead(
        id=user_id,
        email=user_email,
        full_name=user_full_name,
        is_active=user_is_active,
        is_superuser=user_is_superuser,
        created_at=user_created_at
    )

    access_token = create_access_token(
        subject=str(user_id),
        extra_claims={"email": user_email}
    )
    csrf_token = generate_csrf_token(str(user_id))
    set_auth_cookies(response, access_token, raw_refresh_token, csrf_token)

    return TokenResponse(
        access_token=access_token,
        expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        csrf_token=csrf_token,
        user=user_read,
        workspaces=workspaces
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_tokens(
    request: Request,
    response: Response,
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
    x_refresh_token: Optional[str] = Header(None, alias="X-Refresh-Token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Rotates refresh tokens and detects reuse attacks.
    If a revoked refresh token is presented, the entire token family is revoked immediately.
    """
    token_str = refresh_token_cookie or x_refresh_token
    if not token_str:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )

    token_hash = hash_token(token_str)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored_token = result.scalar_one_or_none()

    if not stored_token:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    token_id = str(stored_token.id)
    token_user_id = stored_token.user_id
    token_family_id = stored_token.family_id
    token_is_revoked = stored_token.is_revoked
    token_expires_at = stored_token.expires_at

    if token_is_revoked:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == token_family_id)
            .values(is_revoked=True)
        )
        audit = AuditLog(
            workspace_id=None,
            user_id=token_user_id,
            action="SECURITY_TOKEN_REUSE_DETECTED",
            resource_type="refresh_token",
            resource_id=token_id,
            details={"family_id": str(token_family_id)},
            ip_address=request.client.host if request.client else None
        )
        db.add(audit)
        await db.commit()
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Security alert: Token reuse detected. Session invalidated."
        )

    # Normalize tzinfo for comparison
    if token_expires_at.tzinfo is None:
        token_expires_at = token_expires_at.replace(tzinfo=timezone.utc)

    if token_expires_at < datetime.now(timezone.utc):
        stored_token.is_revoked = True
        await db.commit()
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )

    raw_new_token, new_hash = generate_refresh_token()
    stored_token.is_revoked = True
    stored_token.replaced_by_hash = new_hash

    new_token_record = RefreshToken(
        user_id=token_user_id,
        token_hash=new_hash,
        family_id=token_family_id,
        is_revoked=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(new_token_record)
    await db.commit()

    new_access_token = create_access_token(subject=str(token_user_id))
    csrf_token = generate_csrf_token(str(token_user_id))
    set_auth_cookies(response, new_access_token, raw_new_token, csrf_token)

    return RefreshResponse(
        access_token=new_access_token,
        expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        csrf_token=csrf_token
    )


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logs out user, revokes token family in database, and clears cookies."""
    if refresh_token_cookie:
        token_hash = hash_token(refresh_token_cookie)
        result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        token = result.scalar_one_or_none()
        if token:
            token_id = str(token.id)
            token_user_id = token.user_id
            token_family_id = token.family_id
            await db.execute(
                update(RefreshToken)
                .where(RefreshToken.family_id == token_family_id)
                .values(is_revoked=True)
            )
            audit = AuditLog(
                workspace_id=None,
                user_id=current_user.id if current_user else token_user_id,
                action="AUTH_LOGOUT",
                resource_type="user",
                resource_id=token_id,
                details={"family_id": str(token_family_id)}
            )
            db.add(audit)
            await db.commit()

    clear_auth_cookies(response)
    return {"detail": "Successfully logged out"}


@router.get("/me", response_model=TokenResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns the authenticated user's profile and active workspace memberships."""
    ws_query = (
        select(Workspace, WorkspaceMembership.role)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
        .where(
            WorkspaceMembership.user_id == current_user.id,
            WorkspaceMembership.is_active.is_(True),
            Workspace.is_active.is_(True)
        )
    )
    ws_results = await db.execute(ws_query)
    workspaces: List[WorkspaceRead] = [
        WorkspaceRead(
            id=ws.id,
            organization_id=ws.organization_id,
            name=ws.name,
            is_active=ws.is_active,
            role=role.value,
            created_at=ws.created_at
        )
        for ws, role in ws_results.all()
    ]

    user_id = current_user.id
    csrf_token = generate_csrf_token(str(user_id))
    access_token = create_access_token(subject=str(user_id))

    user_read = UserRead(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        created_at=current_user.created_at
    )

    return TokenResponse(
        access_token=access_token,
        expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        csrf_token=csrf_token,
        user=user_read,
        workspaces=workspaces
    )
