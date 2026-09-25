"""Authentication service — handles user registration, login, and JWT tokens."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import Organization, User
from app.schemas.auth import AuthResponse, OrganizationResponse, TokenData, UserResponse

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, organization_id: str) -> str:
    """Create a signed JWT token."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": user_id,
        "org": organization_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[TokenData]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        organization_id = payload.get("org")
        if user_id is None or organization_id is None:
            return None
        return TokenData(user_id=user_id, organization_id=organization_id)
    except JWTError:
        return None


def _slugify(name: str) -> str:
    """Convert organization name to URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '-', slug)
    return f"{slug}-{uuid.uuid4().hex[:6]}"


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    organization_name: str,
) -> AuthResponse:
    """Register a new user and create their organization."""
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise ValueError("An account with this email already exists")

    org = Organization(
        name=organization_name,
        slug=_slugify(organization_name),
        plan="free",
    )
    db.add(org)
    await db.flush()

    user = User(
        organization_id=org.id,
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role="owner",
    )
    db.add(user)
    await db.flush()

    token = create_access_token(str(user.id), str(org.id))

    return AuthResponse(
        access_token=token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            organization_id=str(user.organization_id),
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else "",
        ),
        organization=OrganizationResponse(
            id=str(org.id),
            name=org.name,
            slug=org.slug,
            plan=org.plan,
            created_at=org.created_at.isoformat() if org.created_at else "",
        ),
    )


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> AuthResponse:
    """Authenticate a user with email + password."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(password, user.password_hash):
        raise ValueError("Invalid email or password")

    if not user.is_active:
        raise ValueError("Account is deactivated")

    result = await db.execute(
        select(Organization).where(Organization.id == user.organization_id)
    )
    org = result.scalar_one()

    token = create_access_token(str(user.id), str(org.id))

    return AuthResponse(
        access_token=token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            organization_id=str(user.organization_id),
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else "",
        ),
        organization=OrganizationResponse(
            id=str(org.id),
            name=org.name,
            slug=org.slug,
            plan=org.plan,
            created_at=org.created_at.isoformat() if org.created_at else "",
        ),
    )
