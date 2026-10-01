"""Customer model — stores parsed and enriched customer data (MongoDB Edition)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any


class Customer:
    """A business customer extracted from uploaded data."""

    def __init__(
        self,
        id: Optional[str] = None,
        organization_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        external_id: str = "",
        name: Optional[str] = None,
        email: Optional[str] = None,
        region: Optional[str] = None,
        total_spent: Optional[float] = 0.0,
        order_count: Optional[int] = 0,
        first_purchase: Optional[datetime] = None,
        last_purchase: Optional[datetime] = None,
        segment: Optional[str] = None,
        churn_risk_score: Optional[float] = None,
        churn_risk_level: Optional[str] = None,
        estimated_clv: Optional[float] = None,
        created_at: Optional[datetime] = None,
        **kwargs: Any,
    ):
        self.id = str(id or uuid.uuid4())
        self.organization_id = str(organization_id) if organization_id else ""
        self.dataset_id = str(dataset_id) if dataset_id else ""
        self.external_id = external_id
        self.name = name
        self.email = email
        self.region = region
        self.total_spent = total_spent or 0.0
        self.order_count = order_count or 0
        self.first_purchase = first_purchase
        self.last_purchase = last_purchase
        self.segment = segment
        self.churn_risk_score = churn_risk_score
        self.churn_risk_level = churn_risk_level
        self.estimated_clv = estimated_clv
        self.created_at = created_at or datetime.now(timezone.utc)

    def to_doc(self) -> Dict[str, Any]:
        """Convert to MongoDB document format."""
        return {
            "_id": self.id,
            "id": self.id,
            "organization_id": self.organization_id,
            "dataset_id": self.dataset_id,
            "external_id": self.external_id,
            "name": self.name,
            "email": self.email,
            "region": self.region,
            "total_spent": self.total_spent,
            "order_count": self.order_count,
            "first_purchase": self.first_purchase,
            "last_purchase": self.last_purchase,
            "segment": self.segment,
            "churn_risk_score": self.churn_risk_score,
            "churn_risk_level": self.churn_risk_level,
            "estimated_clv": self.estimated_clv,
            "created_at": self.created_at,
        }

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]) -> Optional[Customer]:
        if not doc:
            return None
        return cls(
            id=str(doc.get("id") or doc.get("_id")),
            organization_id=str(doc.get("organization_id", "")),
            dataset_id=str(doc.get("dataset_id", "")),
            external_id=doc.get("external_id", ""),
            name=doc.get("name"),
            email=doc.get("email"),
            region=doc.get("region"),
            total_spent=doc.get("total_spent", 0.0),
            order_count=doc.get("order_count", 0),
            first_purchase=doc.get("first_purchase"),
            last_purchase=doc.get("last_purchase"),
            segment=doc.get("segment"),
            churn_risk_score=doc.get("churn_risk_score"),
            churn_risk_level=doc.get("churn_risk_level"),
            estimated_clv=doc.get("estimated_clv"),
            created_at=doc.get("created_at"),
        )
