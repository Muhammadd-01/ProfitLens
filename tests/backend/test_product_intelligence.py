"""Unit tests for Product Performance & Intelligence Service."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.services.product_intelligence_service import (
    compute_product_metrics,
    compute_product_growth_rates,
    classify_bcg_quadrants,
    compute_product_pareto_curve,
)


@pytest.fixture
def sample_product_transactions():
    """Generates synthetic product transactions spanning two periods for 4 distinct product archetypes:
    - PROD-STAR: High relative market share, high growth
    - PROD-COW: High relative market share, low/negative growth
    - PROD-QM: Low relative market share, high growth
    - PROD-DOG: Low relative market share, low/negative growth
    """
    start_date = datetime(2023, 1, 1, 10, 0, 0)
    records = []

    # Period 1 (Days 0 to 14) vs Period 2 (Days 15 to 30)
    # 1. STAR: Period 1 = 10 orders @ $100 = $1,000; Period 2 = 30 orders @ $100 = $3,000 (+200% growth)
    for i in range(10):
        records.append({
            "order_id": f"ORD-STAR-P1-{i}",
            "product_id": "PROD-STAR",
            "product_name": "Premium Smartphone Pro",
            "category": "Electronics",
            "order_date": start_date + timedelta(days=i),
            "revenue": 100.0,
            "quantity": 1,
            "status": "delivered",
        })
    for i in range(30):
        records.append({
            "order_id": f"ORD-STAR-P2-{i}",
            "product_id": "PROD-STAR",
            "product_name": "Premium Smartphone Pro",
            "category": "Electronics",
            "order_date": start_date + timedelta(days=16 + (i % 14)),
            "revenue": 100.0,
            "quantity": 1,
            "status": "delivered",
        })

    # 2. CASH COW: Period 1 = 25 orders @ $100 = $2,500; Period 2 = 20 orders @ $100 = $2,000 (-20% growth)
    for i in range(25):
        records.append({
            "order_id": f"ORD-COW-P1-{i}",
            "product_id": "PROD-COW",
            "product_name": "Standard Laptop Base",
            "category": "Electronics",
            "order_date": start_date + timedelta(days=i % 14),
            "revenue": 100.0,
            "quantity": 1,
            "status": "delivered",
        })
    for i in range(20):
        records.append({
            "order_id": f"ORD-COW-P2-{i}",
            "product_id": "PROD-COW",
            "product_name": "Standard Laptop Base",
            "category": "Electronics",
            "order_date": start_date + timedelta(days=16 + (i % 14)),
            "revenue": 100.0,
            "quantity": 1,
            "status": "delivered",
        })

    # 3. QUESTION MARK: Period 1 = 2 orders @ $50 = $100; Period 2 = 8 orders @ $50 = $400 (+300% growth, low share)
    for i in range(2):
        records.append({
            "order_id": f"ORD-QM-P1-{i}",
            "product_id": "PROD-QM",
            "product_name": "Smart Watch Sport",
            "category": "Electronics",
            "order_date": start_date + timedelta(days=i * 5),
            "revenue": 50.0,
            "quantity": 1,
            "status": "delivered",
        })
    for i in range(8):
        records.append({
            "order_id": f"ORD-QM-P2-{i}",
            "product_id": "PROD-QM",
            "product_name": "Smart Watch Sport",
            "category": "Electronics",
            "order_date": start_date + timedelta(days=16 + i),
            "revenue": 50.0,
            "quantity": 1,
            "status": "delivered",
        })

    # 4. DOG: Period 1 = 3 orders @ $20 = $60; Period 2 = 1 order @ $20 = $20 (-66% growth, low share, 1 return)
    for i in range(3):
        records.append({
            "order_id": f"ORD-DOG-P1-{i}",
            "product_id": "PROD-DOG",
            "product_name": "Old USB Cable 2.0",
            "category": "Electronics",
            "order_date": start_date + timedelta(days=i * 4),
            "revenue": 20.0,
            "quantity": 1,
            "status": "delivered",
        })
    records.append({
        "order_id": "ORD-DOG-P2-0",
        "product_id": "PROD-DOG",
        "product_name": "Old USB Cable 2.0",
        "category": "Electronics",
        "order_date": start_date + timedelta(days=22),
        "revenue": 20.0,
        "quantity": 1,
        "status": "returned",
    })

    return pd.DataFrame(records)


def test_compute_product_metrics(sample_product_transactions):
    """Verify aggregation across revenue, units, orders, ASP, and return rate."""
    metrics = compute_product_metrics(
        df=sample_product_transactions,
        product_id_col="product_id",
        revenue_col="revenue",
        date_col="order_date",
        quantity_col="quantity",
        category_col="category",
        product_name_col="product_name",
        status_col="status",
    )

    assert len(metrics) == 4
    prod_star = metrics[metrics["product_id"] == "PROD-STAR"].iloc[0]
    assert prod_star["revenue"] == 4000.0
    assert prod_star["units_sold"] == 40
    assert prod_star["avg_price"] == 100.0
    assert prod_star["return_rate_pct"] == 0.0

    prod_dog = metrics[metrics["product_id"] == "PROD-DOG"].iloc[0]
    assert prod_dog["revenue"] == 80.0
    assert prod_dog["units_sold"] == 4
    assert prod_dog["return_count"] == 1
    assert prod_dog["return_rate_pct"] == 25.0  # 1 return out of 4 orders


def test_compute_product_growth_rates(sample_product_transactions):
    """Verify period-over-period growth calculation."""
    growth = compute_product_growth_rates(
        df=sample_product_transactions,
        product_id_col="product_id",
        revenue_col="revenue",
        date_col="order_date",
    )

    # STAR surged from $1000 to $3000 -> +200%
    assert growth["PROD-STAR"] == 200.0
    # COW dropped from $2500 to $2000 -> -20%
    assert growth["PROD-COW"] == -20.0
    # QM surged from $100 to $400 -> +300%
    assert growth["PROD-QM"] == 300.0
    # DOG dropped from $60 to $20 -> -66.7%
    assert growth["PROD-DOG"] < 0.0


def test_classify_bcg_quadrants(sample_product_transactions):
    """Verify correct BCG quadrant assignments (Star, Cash Cow, Question Mark, Dog)."""
    metrics = compute_product_metrics(
        df=sample_product_transactions,
        product_id_col="product_id",
        revenue_col="revenue",
        date_col="order_date",
        category_col="category",
    )
    growth = compute_product_growth_rates(
        df=sample_product_transactions,
        product_id_col="product_id",
        revenue_col="revenue",
        date_col="order_date",
    )

    bcg_df = classify_bcg_quadrants(
        products_df=metrics,
        growth_rates=growth,
        product_id_col="product_id",
        category_col="category",
    )

    classes = dict(zip(bcg_df["product_id"], bcg_df["bcg_category"]))
    assert classes["PROD-STAR"] == "star"
    assert classes["PROD-COW"] == "cash_cow"
    assert classes["PROD-QM"] == "question_mark"
    assert classes["PROD-DOG"] == "dog"

    # Verify recommendations are populated
    for rec in bcg_df["recommendation"]:
        assert len(rec) > 10


def test_compute_product_pareto_curve(sample_product_transactions):
    """Verify Pareto 80/20 distribution and ABC ranking."""
    metrics = compute_product_metrics(
        df=sample_product_transactions,
        product_id_col="product_id",
        revenue_col="revenue",
        date_col="order_date",
        product_name_col="product_name",
    )

    pareto_df, points = compute_product_pareto_curve(
        products_df=metrics,
        product_id_col="product_id",
        product_name_col="product_name",
    )

    assert len(points) == 4
    assert points[0].product_id == "PROD-COW" or points[0].product_id == "PROD-STAR"
    # Total revenue = 4000 + 4500 + 500 + 80 = 9080
    # Top 2 products (STAR + COW = 8500 / 9080 = 93.6%)
    classes = dict(zip(pareto_df["product_id"], pareto_df["pareto_class"]))
    assert classes["PROD-COW"] in ["A", "B"]
    assert classes["PROD-STAR"] in ["A", "B"]
    assert classes["PROD-DOG"] == "C"
