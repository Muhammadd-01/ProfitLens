from __future__ import annotations

import pytest
from app.utils.constants import (
    COLUMN_PATTERNS,
    MIN_DATA_REQUIREMENTS,
    DatasetStatus,
    AnalysisType,
    ChurnRiskLevel,
    ProductPerformanceTier,
)


def test_column_mapping_patterns_exist():
    """Verify essential business column patterns are configured for auto-detection."""
    required_keys = [
        "customer_id",
        "order_id",
        "product_id",
        "order_date",
        "revenue",
        "quantity",
        "category",
        "region",
    ]
    for key in required_keys:
        assert key in COLUMN_PATTERNS
        assert len(COLUMN_PATTERNS[key]) > 0
        assert all(isinstance(pattern, str) for pattern in COLUMN_PATTERNS[key])


def test_ml_data_requirements_thresholds():
    """Verify safety thresholds for machine learning models."""
    assert "kpis" in MIN_DATA_REQUIREMENTS
    assert "segmentation" in MIN_DATA_REQUIREMENTS
    assert "churn" in MIN_DATA_REQUIREMENTS
    assert "forecast" in MIN_DATA_REQUIREMENTS
    assert "anomaly" in MIN_DATA_REQUIREMENTS

    # Verify segmentation has minimum requirements
    assert MIN_DATA_REQUIREMENTS["segmentation"]["min_customers"] >= 50
    assert MIN_DATA_REQUIREMENTS["churn"]["min_customers"] >= 100
    assert MIN_DATA_REQUIREMENTS["forecast"]["min_orders"] >= 100


def test_enums_integrity():
    """Verify enum values match domain rules."""
    assert DatasetStatus.READY.value == "ready"
    assert DatasetStatus.ERROR.value == "error"
    assert ChurnRiskLevel.CRITICAL.value == "critical"
    assert ProductPerformanceTier.TOP_PERFORMER.value == "top_performer"
