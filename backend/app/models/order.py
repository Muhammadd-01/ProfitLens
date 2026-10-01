"""Order model — transactional record (MongoDB Edition)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any


class Order:
    """A single order/transaction from uploaded data."""

    def __init__(
        self,
        id: Optional[str] = None,
        organization_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        external_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        product_id: Optional[str] = None,
        order_date: Optional[datetime] = None,
        amount: Optional[float] = None,
        discount: Optional[float] = 0.0,
        quantity: Optional[int] = 1,
        status: Optional[str] = None,
        region: Optional[str] = None,
        channel: Optional[str] = None,
        is_anomaly: Optional[bool] = False,
        anomaly_score: Optional[float] = None,
        created_at: Optional[datetime] = None,
        **kwargs: Any,
    ):
        self.id = str(id or uuid.uuid4())
        self.organization_id = str(organization_id) if organization_id else ""
        self.dataset_id = str(dataset_id) if dataset_id else ""
        self.external_id = external_id
        self.customer_id = str(customer_id) if customer_id else None
        self.product_id = str(product_id) if product_id else None
        self.order_date = order_date
        self.amount = amount
        self.discount = discount or 0.0
        self.quantity = quantity or 1
        self.status = status
        self.region = region
        self.channel = channel
        self.is_anomaly = is_anomaly or False
        self.anomaly_score = anomaly_score
        self.created_at = created_at or datetime.now(timezone.utc)

    def to_doc(self) -> Dict[str, Any]:
        """Convert to MongoDB document format."""
        return {
            "_id": self.id,
            "id": self.id,
            "organization_id": self.organization_id,
            "dataset_id": self.dataset_id,
            "external_id": self.external_id,
            "customer_id": self.customer_id,
            "product_id": self.product_id,
            "order_date": self.order_date,
            "amount": self.amount,
            "discount": self.discount,
            "quantity": self.quantity,
            "status": self.status,
            "region": self.region,
            "channel": self.channel,
            "is_anomaly": self.is_anomaly,
            "anomaly_score": self.anomaly_score,
            "created_at": self.created_at,
        }

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]) -> Optional[Order]:
        if not doc:
            return None
        return cls(
            id=str(doc.get("id") or doc.get("_id")),
            organization_id=str(doc.get("organization_id", "")),
            dataset_id=str(doc.get("dataset_id", "")),
            external_id=doc.get("external_id"),
            customer_id=str(doc.get("customer_id")) if doc.get("customer_id") else None,
            product_id=str(doc.get("product_id")) if doc.get("product_id") else None,
            order_date=doc.get("order_date"),
            amount=doc.get("amount"),
            discount=doc.get("discount", 0.0),
            quantity=doc.get("quantity", 1),
            status=doc.get("status"),
            region=doc.get("region"),
            channel=doc.get("channel"),
            is_anomaly=doc.get("is_anomaly", False),
            anomaly_score=doc.get("anomaly_score"),
            created_at=doc.get("created_at"),
        )
