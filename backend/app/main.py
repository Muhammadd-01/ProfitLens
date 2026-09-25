from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api.auth import router as auth_router
from app.api.datasets import router as datasets_router
from app.api.analytics import router as analytics_router
from app.api.ml import router as ml_router
from app.api.insights import router as insights_router
from app.api.reports import router as reports_router

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Turn Business Data Into Profitable Decisions.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Robust CORS middleware configuration
allowed_origins = list(set([
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
] + (settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [])))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler guaranteeing CORS headers and user-friendly diagnostics on 500s."""
    origin = request.headers.get("origin", "http://localhost:5173")
    err_str = str(exc)

    if "nodename nor servname" in err_str or "gaierror" in err_str or "CannotConnectNowError" in err_str:
        detail = (
            "Database Connection Error: Could not resolve Supabase host. "
            "Please check that DATABASE_URL in your .env file is set to your active Supabase connection string. "
            "(The current URL contains placeholder text like [project-ref] or [password])."
        )
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif "ConnectionRefusedError" in err_str or "password authentication failed" in err_str:
        detail = (
            "Database Authentication Error: Connection was refused or password incorrect. "
            "Please check your PostgreSQL credentials in .env."
        )
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        detail = f"Server Error: {err_str}"
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept",
        },
    )


# Register API routers
app.include_router(auth_router, prefix="/api")
app.include_router(datasets_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(ml_router, prefix="/api")
app.include_router(insights_router, prefix="/api")
app.include_router(reports_router, prefix="/api")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/api")
async def api_root():
    """API root with available endpoints."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
        "health": "/api/health",
        "endpoints": {
            "auth": "/api/auth",
            "datasets": "/api/datasets",
            "analytics": "/api/analytics",
            "ml": "/api/ml",
            "insights": "/api/insights",
            "reports": "/api/reports",
        },
    }
