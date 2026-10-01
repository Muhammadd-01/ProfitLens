"""Product model — stores parsed product data and performance metrics (MongoDB Edition)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any


class Product:
    """A product/service extracted from uploaded data."""

    def __init__(
        self,
        id: Optional[str] = None,
        organization_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        external_id: str = "",
        name: Optional[str] = None,
        category: Optional[str] = None,
        unit_price: Optional[float] = None,
        total_revenue: Optional[float] = 0.0,
        units_sold: Optional[int] = 0,
        order_count: Optional[int] = 0,
        performance_tier: Optional[str] = None,
        created_at: Optional[datetime] = None,
        **kwargs: Any,
    ):
        self.id = str(id or uuid.uuid4())
        self.organization_id = str(organization_id) if organization_id else ""
        self.dataset_id = str(dataset_id) if dataset_id else ""
        self.external_id = external_id
        self.name = name
        self.category = category
        self.unit_price = unit_price
        self.total_revenue = total_revenue or 0.0
        self.units_sold = units_sold or 0
        self.order_count = order_count or 0
        self.performance_tier = performance_tier
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
            "category": self.category,
            "unit_price": self.unit_price,
            "total_revenue": self.total_revenue,
            "units_sold": self.units_sold,
            "order_count": self.order_count,
            "performance_tier": self.performance_tier,
            "created_at": self.created_at,
        }

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]) -> Optional[Product]:
        if not doc:
            return None
        return cls(
            id=str(doc.get("id") or doc.get("_id")),
            organization_id=str(doc.get("organization_id", "")),
            dataset_id=str(doc.get("dataset_id", "")),
            external_id=doc.get("external_id", ""),
            name=doc.get("name"),
            category=doc.get("category"),
            unit_price=doc.get("unit_price"),
            total_revenue=doc.get("total_revenue", 0.0),
            units_sold=doc.get("units_sold", 0),
            order_count=doc.get("order_count", 0),
            performance_tier=doc.get("performance_tier"),
            created_at=doc.get("created_at"),
        )
