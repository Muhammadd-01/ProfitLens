"""User and Organization models for ProfitLens (MongoDB Edition).

Foundation of multi-tenancy in ProfitLens.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List


class Organization:
    """A business/company account — top-level tenant boundary."""

    def __init__(
        self,
        id: Optional[str] = None,
        name: str = "",
        slug: str = "",
        plan: str = "free",
        settings: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        **kwargs: Any,
    ):
        self.id = str(id or uuid.uuid4())
        self.name = name
        self.slug = slug
        self.plan = plan
        self.settings = settings or {}
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def to_doc(self) -> Dict[str, Any]:
        """Convert to MongoDB document format."""
        return {
            "_id": self.id,
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "plan": self.plan,
            "settings": self.settings,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]) -> Optional[Organization]:
        if not doc:
            return None
        return cls(
            id=str(doc.get("id") or doc.get("_id")),
            name=doc.get("name", ""),
            slug=doc.get("slug", ""),
            plan=doc.get("plan", "free"),
            settings=doc.get("settings", {}),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
        )


class User:
    """An individual user account."""

    def __init__(
        self,
        id: Optional[str] = None,
        organization_id: Optional[str] = None,
        email: str = "",
        password_hash: str = "",
        full_name: str = "",
        role: str = "owner",
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        **kwargs: Any,
    ):
        self.id = str(id or uuid.uuid4())
        self.organization_id = str(organization_id) if organization_id else ""
        self.email = email
        self.password_hash = password_hash
        self.full_name = full_name
        self.role = role
        self.is_active = is_active
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def to_doc(self) -> Dict[str, Any]:
        """Convert to MongoDB document format."""
        return {
            "_id": self.id,
            "id": self.id,
            "organization_id": self.organization_id,
            "email": self.email,
            "password_hash": self.password_hash,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]) -> Optional[User]:
        if not doc:
            return None
        return cls(
            id=str(doc.get("id") or doc.get("_id")),
            organization_id=str(doc.get("organization_id", "")),
            email=doc.get("email", ""),
            password_hash=doc.get("password_hash") or doc.get("hashed_password", ""),
            full_name=doc.get("full_name", ""),
            role=doc.get("role", "owner"),
            is_active=doc.get("is_active", True),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
        )
