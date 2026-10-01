"""Review model — stores customer review text and NLP results (MongoDB Edition)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any


class Review:
    """A customer review with NLP-derived sentiment and topics."""

    def __init__(
        self,
        id: Optional[str] = None,
        organization_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        product_id: Optional[str] = None,
        review_text: Optional[str] = None,
        rating: Optional[float] = None,
        review_date: Optional[datetime] = None,
        sentiment_score: Optional[float] = None,
        sentiment_label: Optional[str] = None,
        topics: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        **kwargs: Any,
    ):
        self.id = str(id or uuid.uuid4())
        self.organization_id = str(organization_id) if organization_id else ""
        self.dataset_id = str(dataset_id) if dataset_id else ""
        self.customer_id = str(customer_id) if customer_id else None
        self.product_id = str(product_id) if product_id else None
        self.review_text = review_text
        self.rating = rating
        self.review_date = review_date
        self.sentiment_score = sentiment_score
        self.sentiment_label = sentiment_label
        self.topics = topics or {}
        self.created_at = created_at or datetime.now(timezone.utc)

    def to_doc(self) -> Dict[str, Any]:
        """Convert to MongoDB document format."""
        return {
            "_id": self.id,
            "id": self.id,
            "organization_id": self.organization_id,
            "dataset_id": self.dataset_id,
            "customer_id": self.customer_id,
            "product_id": self.product_id,
            "review_text": self.review_text,
            "rating": self.rating,
            "review_date": self.review_date,
            "sentiment_score": self.sentiment_score,
            "sentiment_label": self.sentiment_label,
            "topics": self.topics,
            "created_at": self.created_at,
        }

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]) -> Optional[Review]:
        if not doc:
            return None
        return cls(
            id=str(doc.get("id") or doc.get("_id")),
            organization_id=str(doc.get("organization_id", "")),
            dataset_id=str(doc.get("dataset_id", "")),
            customer_id=str(doc.get("customer_id")) if doc.get("customer_id") else None,
            product_id=str(doc.get("product_id")) if doc.get("product_id") else None,
            review_text=doc.get("review_text"),
            rating=doc.get("rating"),
            review_date=doc.get("review_date"),
            sentiment_score=doc.get("sentiment_score"),
            sentiment_label=doc.get("sentiment_label"),
            topics=doc.get("topics") or {},
            created_at=doc.get("created_at"),
        )
