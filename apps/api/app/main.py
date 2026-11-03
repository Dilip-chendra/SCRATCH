from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.health import router as health_router
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.security import verify_csrf_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="SCRATCH API",
    description="AI Growth Operations & Sales Intelligence Platform - Foundational API",
    version="0.1.0",
    lifespan=lifespan
)

# 1. Credentialed CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-CSRF-Token"]
)


# 2. CSRF Defense Middleware for Cookie-Authenticated Requests
@app.middleware("http")
async def csrf_protection_middleware(request: Request, call_next):
    # Safe HTTP methods do not require CSRF token
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return await call_next(request)

    # Public authentication & docs entrypoints
    exempt_paths = {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/docs",
        "/openapi.json"
    }
    if request.url.path in exempt_paths:
        return await call_next(request)

    # If the request is authenticated via cookie, check CSRF token
    access_cookie = request.cookies.get("access_token")
    if access_cookie:
        csrf_header = request.headers.get("X-CSRF-Token")
        csrf_cookie = request.cookies.get("csrf_token")
        
        # Double Submit verification
        if not csrf_header or not csrf_cookie or csrf_header != csrf_cookie:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF validation failed: Missing or mismatched X-CSRF-Token"}
            )

    return await call_next(request)


# 3. Mount Routers
app.include_router(health_router)
app.include_router(api_v1_router)
