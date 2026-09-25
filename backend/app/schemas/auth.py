"""Authentication schemas — request/response models for auth endpoints."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Registration request body."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    organization_name: str = Field(..., min_length=1, max_length=255)


class LoginRequest(BaseModel):
    """Login request body."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User data returned in API responses."""
    id: str
    email: str
    full_name: str
    role: str
    organization_id: str
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class OrganizationResponse(BaseModel):
    """Organization data returned in API responses."""
    id: str
    name: str
    slug: str
    plan: str
    created_at: str

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Response after successful login/registration."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    organization: OrganizationResponse


class TokenData(BaseModel):
    """Data extracted from JWT token."""
    user_id: str
    organization_id: str
