from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import init_db, close_db
from app.api.auth import router as auth_router
from app.api.datasets import router as datasets_router
from app.api.analytics import router as analytics_router
from app.api.ml import router as ml_router
from app.api.insights import router as insights_router
from app.api.reports import router as reports_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: initialize MongoDB indexes on startup, close connections on shutdown."""
    try:
        await init_db()
    except Exception as exc:
        print(f"Warning: Could not initialize MongoDB indexes on startup: {exc}")
    yield
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Turn Business Data Into Profitable Decisions.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
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

    if (
        "ServerSelectionTimeoutError" in err_str
        or "ConnectionRefusedError" in err_str
        or "could not connect to server" in err_str
    ):
        detail = (
            "Database Connection Error: Could not connect to MongoDB. "
            "Please ensure MongoDB is running (e.g. locally on mongodb://localhost:27017 for MongoDB Compass) "
            "and check MONGODB_URL in your .env file."
        )
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif "OperationFailure" in err_str and "auth" in err_str.lower():
        detail = (
            "Database Authentication Error: MongoDB authentication failed. "
            "Please verify your credentials in MONGODB_URL in .env."
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
