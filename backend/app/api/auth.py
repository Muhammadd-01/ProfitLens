"""Authentication API routes — login, register, and user info endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, AuthResponse, UserResponse
from app.services.auth_service import authenticate_user, register_user
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user and create their organization."""
    from app.config import get_settings
    settings = get_settings()
    if "[YOUR-DATABASE-PASSWORD]" in settings.DATABASE_URL or "[YOUR-PASSWORD]" in settings.DATABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database Password Required: Your .env file currently has '[YOUR-DATABASE-PASSWORD]'. Please set your actual Supabase PostgreSQL password in .env to connect.",
        )

    try:
        return await register_user(
            db=db,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            organization_name=request.organization_name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        err_msg = str(e)
        if "nodename nor servname" in err_msg or "gaierror" in err_msg or "CannotConnectNowError" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database Connection Error: Could not connect to Supabase/PostgreSQL. Please update your .env file with your real Supabase connection string.",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {err_msg}",
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email and password."""
    from app.config import get_settings
    settings = get_settings()
    if "[YOUR-DATABASE-PASSWORD]" in settings.DATABASE_URL or "[YOUR-PASSWORD]" in settings.DATABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database Password Required: Your .env file currently has '[YOUR-DATABASE-PASSWORD]'. Please set your actual Supabase PostgreSQL password in .env to connect.",
        )

    try:
        return await authenticate_user(
            db=db,
            email=request.email,
            password=request.password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        err_msg = str(e)
        if "nodename nor servname" in err_msg or "gaierror" in err_msg or "CannotConnectNowError" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database Connection Error: Could not connect to Supabase/PostgreSQL. Please update your .env file with your real Supabase connection string.",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {err_msg}",
        )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user=Depends(get_current_user),
):
    """Get the currently authenticated user's profile."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        organization_id=str(current_user.organization_id),
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat() if current_user.created_at else "",
    )
