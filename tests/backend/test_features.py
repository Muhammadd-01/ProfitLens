"""Unit tests for Feature Engineering Service (Customer RFM and Time-Series Features)."""

import pytest
import pandas as pd
import numpy as np

from app.services.feature_service import (
    compute_customer_rfm_features,
    compute_timeseries_features,
)


def test_compute_customer_rfm_features():
    """Verify RFM, lifespan, AOV, inter-arrival time, and catalog generation."""
    data = {
        "customer_id": ["C1", "C1", "C2", "C3", "C3", "C3"],
        "order_id": ["O1", "O2", "O3", "O4", "O5", "O6"],
        "order_date": [
            "2023-01-01 10:00:00",
            "2023-01-11 10:00:00",  # C1 has 2 orders, lifespan 10 days, interval 10 days
            "2023-01-15 12:00:00",  # C2 has 1 order, lifespan 0 days, interval 0 days
            "2023-01-05 09:00:00",
            "2023-01-10 09:00:00",
            "2023-01-20 09:00:00",  # C3 has 3 orders, lifespan 15 days, interval 7.5 days
        ],
        "revenue": [50.0, 150.0, 40.0, 100.0, 200.0, 300.0],
        "category": ["Electronics", "Electronics", "Fashion", "Home", "Home", "Home"],
    }
    df = pd.DataFrame(data)

    cust_df, catalog = compute_customer_rfm_features(
        df=df,
        customer_id_col="customer_id",
        date_col="order_date",
        revenue_col="revenue",
        order_id_col="order_id",
        category_col="category",
    )

    assert len(cust_df) == 3
    assert set(cust_df["customer_id"]) == {"C1", "C2", "C3"}

    # Inspect C1
    c1 = cust_df[cust_df["customer_id"] == "C1"].iloc[0]
    assert c1["frequency"] == 2
    assert c1["monetary_total"] == 200.0
    assert c1["avg_order_value"] == 100.0
    assert c1["customer_lifespan_days"] == 10
    assert c1["purchase_interval_mean"] == 10.0
    assert c1["preferred_category"] == "Electronics"

    # Inspect C2 (single order)
    c2 = cust_df[cust_df["customer_id"] == "C2"].iloc[0]
    assert c2["frequency"] == 1
    assert c2["monetary_total"] == 40.0
    assert c2["avg_order_value"] == 40.0
    assert c2["customer_lifespan_days"] == 0
    assert c2["purchase_interval_mean"] == 0.0

    # Inspect C3 (most valuable)
    c3 = cust_df[cust_df["customer_id"] == "C3"].iloc[0]
    assert c3["frequency"] == 3
    assert c3["monetary_total"] == 600.0
    assert c3["avg_order_value"] == 200.0
    assert c3["customer_lifespan_days"] == 15
    assert c3["purchase_interval_mean"] == 7.5

    # Catalog assertions
    catalog_names = {item.name for item in catalog}
    assert "recency_days" in catalog_names
    assert "frequency" in catalog_names
    assert "monetary_total" in catalog_names
    assert "avg_order_value" in catalog_names
    assert "purchase_interval_mean" in catalog_names


def test_compute_timeseries_features():
    """Verify daily regularization, lag shifts, moving averages, and cyclical encoding."""
    dates = pd.date_range(start="2023-01-01", periods=45, freq="D")
    df = pd.DataFrame({
        "order_date": dates,
        "revenue": [100.0 + i * 5 for i in range(45)],
        "order_id": [f"ORD-{i}" for i in range(45)],
    })

    ts_df, catalog = compute_timeseries_features(
        df=df,
        date_col="order_date",
        revenue_col="revenue",
        order_id_col="order_id",
    )

    assert len(ts_df) == 45
    assert "daily_revenue" in ts_df.columns
    assert "revenue_lag_1" in ts_df.columns
    assert "revenue_lag_7" in ts_df.columns
    assert "revenue_rolling_mean_7" in ts_df.columns
    assert "revenue_rolling_std_7" in ts_df.columns
    assert "day_of_week_sin" in ts_df.columns
    assert "day_of_week_cos" in ts_df.columns

    # Verify lag 1 on row 10
    assert ts_df.iloc[10]["revenue_lag_1"] == ts_df.iloc[9]["daily_revenue"]
    # Verify lag 7 on row 10
    assert ts_df.iloc[10]["revenue_lag_7"] == ts_df.iloc[3]["daily_revenue"]

    # Verify cyclical bounds
    assert (ts_df["day_of_week_sin"] >= -1.0).all() and (ts_df["day_of_week_sin"] <= 1.0).all()
    assert (ts_df["day_of_week_cos"] >= -1.0).all() and (ts_df["day_of_week_cos"] <= 1.0).all()

    # Catalog items
    cat_names = {item.name for item in catalog}
    assert "daily_revenue" in cat_names
    assert "revenue_lag_7" in cat_names
    assert "revenue_rolling_mean_7" in cat_names
    assert "revenue_rolling_std_7" in cat_names
