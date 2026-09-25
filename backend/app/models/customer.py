"""Customer model — stores parsed and enriched customer data."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Customer(Base):
    """A business customer extracted from uploaded data."""
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False,
        index=True,
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False,
        index=True,
    )
    
    # From uploaded data
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    region: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Computed metrics
    total_spent: Mapped[Optional[float]] = mapped_column(Float, default=0)
    order_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    first_purchase: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_purchase: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # ML-derived (populated by analysis runs)
    segment: Mapped[Optional[str]] = mapped_column(String(100))
    churn_risk_score: Mapped[Optional[float]] = mapped_column(Float)
    churn_risk_level: Mapped[Optional[str]] = mapped_column(String(50))
    estimated_clv: Mapped[Optional[float]] = mapped_column(Float)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
