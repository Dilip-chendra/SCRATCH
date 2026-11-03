from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.workspaces import router as workspaces_router
from app.api.v1.profile import router as profile_router
from app.api.v1.suppression import router as suppression_router
from app.api.v1.leads import router as leads_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(workspaces_router)
api_v1_router.include_router(health_router)
api_v1_router.include_router(profile_router)
api_v1_router.include_router(suppression_router)
api_v1_router.include_router(leads_router)
