"""Unit tests for Transaction Anomaly Detection Service."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.services.anomaly_service import (
    compute_anomaly_features,
    run_isolation_and_mad_scoring,
    synthesize_anomaly_explanations,
)


@pytest.fixture
def sample_orders_with_anomalies():
    """Generate 60 typical orders ($30-$120) with 3 injected severe anomalies."""
    np.random.seed(42)
    start_date = datetime(2023, 1, 1, 10, 0, 0)
    records = []

    # 60 normal orders across Electronics and Apparel
    for i in range(60):
        cat = "Electronics" if i % 2 == 0 else "Apparel"
        base_rev = 80.0 if cat == "Electronics" else 40.0
        records.append({
            "order_id": f"ORD-NORM-{i}",
            "customer_id": f"CUST-{i % 20}",
            "order_date": start_date + timedelta(hours=i * 2),
            "revenue": round(float(np.random.normal(base_rev, 10.0)), 2),
            "quantity": int(np.random.choice([1, 2, 3])),
            "discount": 0.05,
            "category": cat,
        })

    # Anomaly 1: Massive monetary spike ($4,500 in Apparel where median is ~$40)
    records.append({
        "order_id": "ORD-ANOM-1",
        "customer_id": "CUST-ANOM-1",
        "order_date": start_date + timedelta(days=5, hours=2),
        "revenue": 4500.0,
        "quantity": 1,
        "discount": 0.0,
        "category": "Apparel",
    })

    # Anomaly 2: Extreme bulk quantity (95 units)
    records.append({
        "order_id": "ORD-ANOM-2",
        "customer_id": "CUST-ANOM-2",
        "order_date": start_date + timedelta(days=10, hours=14),
        "revenue": 850.0,
        "quantity": 95,
        "discount": 0.10,
        "category": "Electronics",
    })

    # Anomaly 3: Extreme discount (85% markdown on $1,200 item)
    records.append({
        "order_id": "ORD-ANOM-3",
        "customer_id": "CUST-ANOM-3",
        "order_date": start_date + timedelta(days=12, hours=1),
        "revenue": 1200.0,
        "quantity": 2,
        "discount": 0.85,
        "category": "Electronics",
    })

    return pd.DataFrame(records)


def test_compute_anomaly_features(sample_orders_with_anomalies):
    """Verify feature extraction: category median ratio, quantities, discounts, and velocity."""
    X, data_enriched, feature_cols = compute_anomaly_features(
        df=sample_orders_with_anomalies,
        order_id_col="order_id",
        date_col="order_date",
        revenue_col="revenue",
        cust_col="customer_id",
        qty_col="quantity",
        cat_col="category",
        disc_col="discount",
    )

    assert len(X) == 63
    assert "revenue" in feature_cols
    assert "cat_ratio" in feature_cols
    assert "quantity_feature" in feature_cols
    assert "discount_feature" in feature_cols
    assert "order_velocity_24h" in feature_cols

    # Check that the $4,500 Apparel order has a massive cat_ratio (> 50x)
    anom1_row = data_enriched[data_enriched["order_id"] == "ORD-ANOM-1"].iloc[0]
    assert anom1_row["cat_ratio"] > 30.0


def test_run_isolation_and_mad_scoring(sample_orders_with_anomalies):
    """Verify that Isolation Forest + MAD correctly identifies injected outliers with high anomaly scores."""
    X, data_enriched, _ = compute_anomaly_features(
        df=sample_orders_with_anomalies,
        order_id_col="order_id",
        date_col="order_date",
        revenue_col="revenue",
        cust_col="customer_id",
        qty_col="quantity",
        cat_col="category",
        disc_col="discount",
    )

    scored_df = run_isolation_and_mad_scoring(
        X=X,
        data=data_enriched,
        revenue_col="revenue",
        contamination=0.05,
    )

    assert len(scored_df) == 63
    assert "anomaly_score" in scored_df.columns
    assert (scored_df["anomaly_score"] >= 0.0).all() and (scored_df["anomaly_score"] <= 1.0).all()

    # The 3 injected anomalies should have top-ranking scores
    top_anomalies = scored_df.sort_values("anomaly_score", ascending=False).head(5)["order_id"].values
    assert "ORD-ANOM-1" in top_anomalies
    assert "ORD-ANOM-2" in top_anomalies
    assert "ORD-ANOM-3" in top_anomalies


def test_synthesize_anomaly_explanations(sample_orders_with_anomalies):
    """Verify human-readable root-cause explanations and severity tiers."""
    X, data_enriched, _ = compute_anomaly_features(
        df=sample_orders_with_anomalies,
        order_id_col="order_id",
        date_col="order_date",
        revenue_col="revenue",
        cust_col="customer_id",
        qty_col="quantity",
        cat_col="category",
        disc_col="discount",
    )

    scored_df = run_isolation_and_mad_scoring(
        X=X,
        data=data_enriched,
        revenue_col="revenue",
        contamination=0.05,
    )

    # Inspect Anomaly 1 ($4,500 spike)
    anom1_row = scored_df[scored_df["order_id"] == "ORD-ANOM-1"].iloc[0]
    severity, reason, details = synthesize_anomaly_explanations(anom1_row, "revenue")
    assert severity in ["critical", "high"]
    assert "4,500" in reason or "spike" in reason.lower()
    assert details["amount"] == 4500.0

    # Inspect Anomaly 2 (95 units)
    anom2_row = scored_df[scored_df["order_id"] == "ORD-ANOM-2"].iloc[0]
    severity2, reason2, details2 = synthesize_anomaly_explanations(anom2_row, "revenue")
    assert severity2 in ["critical", "high"]
    assert any("95" in f or "bulk" in f.lower() for f in details2["contributing_factors"])
    assert details2["quantity"] == 95


def test_anomaly_csv_serialization_and_review(tmp_path):
    """Test serializing anomalies to CSV with JSON details and updating review status."""
    import json
    from app.schemas.ml import AnomalyItem

    item = AnomalyItem(
        id="test-anom-123",
        order_id="ORD-999",
        customer_id="CUST-1",
        order_date="2023-01-01 10:00",
        amount=5000.0,
        anomaly_score=0.92,
        severity="critical",
        reason="Extreme monetary spike",
        details={"category_ratio": 25.4, "amount": 5000.0},
        is_reviewed=False,
        review_status="pending",
        detected_at="2023-01-01T10:00:00",
    )

    csv_path = tmp_path / "anomalies.csv"
    rec = item.model_dump()
    rec["details"] = json.dumps(rec["details"])
    df = pd.DataFrame([rec])
    df.to_csv(csv_path, index=False)

    # Reload and verify
    df_read = pd.read_csv(csv_path)
    assert len(df_read) == 1
    assert df_read.iloc[0]["is_reviewed"] == False

    # Simulate review action
    df_read.at[0, "is_reviewed"] = True
    df_read.at[0, "review_status"] = "confirmed_fraud"
    df_read.to_csv(csv_path, index=False)

    df_updated = pd.read_csv(csv_path)
    assert df_updated.iloc[0]["is_reviewed"] == True
    assert df_updated.iloc[0]["review_status"] == "confirmed_fraud"

