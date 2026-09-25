"""Order model — the central transactional record."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
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


class Order(Base):
    """A single order/transaction from uploaded data."""
    __tablename__ = "orders"

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
    external_id: Mapped[Optional[str]] = mapped_column(String(255))
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), index=True
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), index=True
    )
    order_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), index=True
    )
    amount: Mapped[Optional[float]] = mapped_column(Float)
    discount: Mapped[Optional[float]] = mapped_column(Float, default=0)
    quantity: Mapped[Optional[int]] = mapped_column(Integer, default=1)
    status: Mapped[Optional[str]] = mapped_column(String(50))
    region: Mapped[Optional[str]] = mapped_column(String(255))
    channel: Mapped[Optional[str]] = mapped_column(String(100))

    # ML-derived (populated by anomaly detection)
    is_anomaly: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    anomaly_score: Mapped[Optional[float]] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
