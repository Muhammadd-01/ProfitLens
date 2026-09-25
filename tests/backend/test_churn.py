"""Unit tests for Customer Churn Prediction Service."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.services.churn_service import (
    prepare_churn_features_and_target,
    train_churn_classifier,
    score_customer_churn_risks,
)


@pytest.fixture
def sample_transaction_df():
    """Generate 50 customers over 120 days with varying churn behaviors."""
    np.random.seed(42)
    start_date = datetime(2023, 1, 1)
    
    records = []
    # 1. 20 Active Loyalists (transact across all 120 days, frequent return)
    for i in range(20):
        cid = f"CUST-LOYAL-{i}"
        for _ in range(np.random.randint(5, 12)):
            day_offset = np.random.randint(0, 120)
            records.append({
                "customer_id": cid,
                "order_date": start_date + timedelta(days=day_offset),
                "revenue": round(float(np.random.uniform(50.0, 200.0)), 2),
                "order_id": f"ORD-{len(records)}",
            })
            
    # 2. 30 Churned Customers (only purchased in days 0-60, zero purchases in days 61-120)
    for i in range(30):
        cid = f"CUST-CHURN-{i}"
        for _ in range(np.random.randint(1, 4)):
            day_offset = np.random.randint(0, 60)
            records.append({
                "customer_id": cid,
                "order_date": start_date + timedelta(days=day_offset),
                "revenue": round(float(np.random.uniform(20.0, 100.0)), 2),
                "order_id": f"ORD-{len(records)}",
            })

    return pd.DataFrame(records)


def test_prepare_churn_features_and_target(sample_transaction_df):
    """Verify non-leaking window split, feature columns, and target construction."""
    X, y, current_df, feature_cols = prepare_churn_features_and_target(
        raw_df=sample_transaction_df,
        customer_id_col="customer_id",
        date_col="order_date",
        revenue_col="revenue",
        inactivity_days=30,
    )

    assert len(X) > 0
    assert len(y) == len(X)
    assert set(np.unique(y)).issubset({0, 1})
    
    # Check expected features
    expected = [
        "recency_days",
        "frequency",
        "monetary_total",
        "avg_order_value",
        "customer_lifespan_days",
        "purchase_interval_mean",
        "order_velocity",
        "inter_purchase_ratio",
    ]
    assert feature_cols == expected
    for col in expected:
        assert col in X.columns

    # Current features should cover all 50 unique customers
    assert len(current_df) == 50


def test_train_churn_classifier(sample_transaction_df):
    """Verify model training, ROC-AUC bounds, confusion matrix, and feature importances."""
    X, y, _, _ = prepare_churn_features_and_target(
        raw_df=sample_transaction_df,
        customer_id_col="customer_id",
        date_col="order_date",
        revenue_col="revenue",
        inactivity_days=30,
    )

    model, metrics, feature_items, model_name = train_churn_classifier(
        X=X,
        y=y,
        model_type="auto",
    )

    assert model is not None
    assert "Random Forest" in model_name or "Logistic Regression" in model_name

    # Metrics assertions
    assert 0.5 <= metrics.roc_auc <= 1.0
    assert 0.0 <= metrics.precision <= 1.0
    assert 0.0 <= metrics.recall <= 1.0
    assert 0.0 <= metrics.f1_score <= 1.0
    assert 0.0 <= metrics.accuracy <= 1.0

    # Confusion matrix integrity
    cm = metrics.confusion_matrix
    total_test = cm.tp + cm.fp + cm.tn + cm.fn
    assert total_test > 0

    # Feature importance items
    assert len(feature_items) == len(X.columns)
    total_importance = sum(f.importance_score for f in feature_items)
    assert abs(total_importance - 1.0) < 0.05
    for item in feature_items:
        assert len(item.description) > 5


def test_score_customer_churn_risks(sample_transaction_df):
    """Verify individual risk scoring, risk distribution, and revenue at risk."""
    X, y, current_df, feature_cols = prepare_churn_features_and_target(
        raw_df=sample_transaction_df,
        customer_id_col="customer_id",
        date_col="order_date",
        revenue_col="revenue",
        inactivity_days=30,
    )

    model, _, _, _ = train_churn_classifier(X=X, y=y, model_type="auto")

    scored_customers, distribution, total_rev_at_risk = score_customer_churn_risks(
        model=model,
        current_df=current_df,
        feature_cols=feature_cols,
    )

    assert len(scored_customers) == 50
    assert distribution.low_count + distribution.medium_count + distribution.high_count + distribution.critical_count == 50

    # Probabilities must be in [0, 1]
    for c in scored_customers:
        assert 0.0 <= c.churn_risk_score <= 1.0
        assert c.churn_risk_level in ["low", "medium", "high", "critical"]
        assert len(c.top_risk_factors) > 0
        assert len(c.recommended_action) > 10

    # Total revenue at risk should be >= 0
    assert total_rev_at_risk >= 0.0
