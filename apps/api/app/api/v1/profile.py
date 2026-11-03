from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from app.api.deps import TenantContext, get_current_tenant_context, require_role
from app.models.tenancy import WorkspaceRole
from app.models.profile import BusinessProfile
from app.schemas.profile import BusinessProfileResponse, BusinessProfileUpdate

router = APIRouter(prefix="/business-profile", tags=["Business Profile"])


@router.get("", response_model=BusinessProfileResponse)
async def get_business_profile(
    context: TenantContext = Depends(get_current_tenant_context)
):
    """
    Retrieves the business profile for the current workspace.
    If none exists, initializes and returns a default profile.
    """
    stmt = select(BusinessProfile).where(BusinessProfile.workspace_id == context.workspace.id)
    result = await context.session.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        profile = BusinessProfile(
            workspace_id=context.workspace.id,
            company_name=context.workspace.name,
            website_url=None,
            industry=None,
            products_services=[],
            value_propositions=[],
            target_industries=[],
            ideal_customer_profiles=[],
            disqualification_rules=[],
        )
        context.session.add(profile)
        await context.session.flush()

    return profile


@router.put("", response_model=BusinessProfileResponse)
async def update_business_profile(
    payload: BusinessProfileUpdate,
    context: TenantContext = Depends(require_role(WorkspaceRole.MEMBER))
):
    """
    Creates or updates the workspace business profile.
    Requires minimum MEMBER role.
    """
    stmt = select(BusinessProfile).where(BusinessProfile.workspace_id == context.workspace.id)
    result = await context.session.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        profile = BusinessProfile(
            workspace_id=context.workspace.id,
            company_name=payload.company_name,
            website_url=payload.website_url,
            industry=payload.industry,
            products_services=payload.products_services,
            value_propositions=payload.value_propositions,
            target_industries=payload.target_industries,
            ideal_customer_profiles=payload.ideal_customer_profiles,
            disqualification_rules=payload.disqualification_rules,
        )
        context.session.add(profile)
    else:
        profile.company_name = payload.company_name
        profile.website_url = payload.website_url
        profile.industry = payload.industry
        profile.products_services = payload.products_services
        profile.value_propositions = payload.value_propositions
        profile.target_industries = payload.target_industries
        profile.ideal_customer_profiles = payload.ideal_customer_profiles
        profile.disqualification_rules = payload.disqualification_rules

    await context.session.flush()
    return profile
