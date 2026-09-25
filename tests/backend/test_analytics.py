"""Unit tests for Executive Analytics and Business Intelligence Service."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.services.analytics_service import (
    compute_executive_kpis,
    compute_revenue_timeseries,
    compute_category_breakdown,
    compute_top_products,
    calculate_pct_change,
)


def test_calculate_pct_change():
    """Verify relative percentage change calculation and edge case handling."""
    assert calculate_pct_change(120.0, 100.0) == 20.0
    assert calculate_pct_change(80.0, 100.0) == -20.0
    assert calculate_pct_change(100.0, 0.0) is None
    assert calculate_pct_change(100.0, -10.0) is None


def test_compute_executive_kpis():
    """Verify total revenue, orders, customers, AOV, and period-over-period comparisons."""
    # Create 30 days of data where the second half has 50% more revenue
    dates = []
    revenues = []
    order_ids = []
    cust_ids = []

    base_date = datetime(2023, 1, 1)
    for i in range(30):
        dt = base_date + timedelta(days=i)
        # First 15 days: $100 per day; Last 15 days: $150 per day
        rev = 100.0 if i < 15 else 150.0
        dates.append(dt)
        revenues.append(rev)
        order_ids.append(f"ORD-{i}")
        cust_ids.append(f"CUST-{i % 10}")

    df = pd.DataFrame({
        "order_date": dates,
        "revenue": revenues,
        "order_id": order_ids,
        "customer_id": cust_ids,
    })

    kpis, obs = compute_executive_kpis(
        df=df,
        date_col="order_date",
        revenue_col="revenue",
        order_id_col="order_id",
        customer_id_col="customer_id",
    )

    assert kpis.total_revenue == 15 * 100.0 + 15 * 150.0  # 3750.0
    assert kpis.total_orders == 30
    assert kpis.total_customers == 10
    assert kpis.avg_order_value == 125.0
    assert obs.total_days == 29

    # Second half vs first half growth should be +50%
    assert kpis.revenue_change_pct == 50.0
    assert kpis.orders_change_pct == 0.0  # 15 orders in each period


def test_compute_revenue_timeseries():
    """Verify daily regularization, zero-filling, and monthly summaries."""
    dates = [
        datetime(2023, 1, 1),
        datetime(2023, 1, 3),  # Jan 2 has 0 sales
        datetime(2023, 2, 1),
    ]
    df = pd.DataFrame({
        "order_date": dates,
        "revenue": [100.0, 200.0, 300.0],
        "order_id": ["O1", "O2", "O3"],
    })

    daily, monthly = compute_revenue_timeseries(
        df=df,
        date_col="order_date",
        revenue_col="revenue",
        order_id_col="order_id",
    )

    # Daily sequence from Jan 1 to Feb 1 is 32 days
    assert len(daily) == 32
    jan2 = [d for d in daily if d.date == "2023-01-02"][0]
    assert jan2.revenue == 0.0
    assert jan2.orders == 0

    # Monthly sequence: Jan 2023 and Feb 2023
    assert len(monthly) == 2
    assert monthly[0].date == "2023-01"
    assert monthly[0].revenue == 300.0
    assert monthly[1].date == "2023-02"
    assert monthly[1].revenue == 300.0
    assert monthly[1].cumulative_revenue == 600.0


def test_compute_category_breakdown_and_pareto():
    """Verify category shares and Pareto 80/20 tagging."""
    df = pd.DataFrame({
        "category": ["Electronics", "Electronics", "Home", "Fashion", "Books"],
        "revenue": [500.0, 300.0, 150.0, 40.0, 10.0],  # Total = 1000.0
        "order_id": ["O1", "O2", "O3", "O4", "O5"],
    })

    categories = compute_category_breakdown(
        df=df,
        category_col="category",
        revenue_col="revenue",
        order_id_col="order_id",
    )

    assert len(categories) == 4
    # Electronics is 800 (80%), Home is 150 (15%), Fashion is 40 (4%), Books is 10 (1%)
    assert categories[0].category == "Electronics"
    assert categories[0].percentage == 80.0
    assert categories[0].is_pareto_80 is True

    assert categories[1].category == "Home"
    assert categories[1].percentage == 15.0
    # Prior cumulative for Home is 80%, so Home is not strictly in the first 80%
    assert categories[1].is_pareto_80 is False


def test_compute_top_products():
    """Verify top product ranking, unit sales, and average price."""
    df = pd.DataFrame({
        "product_id": ["P1", "P2", "P1", "P3"],
        "revenue": [100.0, 250.0, 100.0, 50.0],
        "quantity": [2, 1, 2, 5],
        "order_id": ["O1", "O2", "O3", "O4"],
    })

    top_prods = compute_top_products(
        df=df,
        product_id_col="product_id",
        revenue_col="revenue",
        quantity_col="quantity",
        order_id_col="order_id",
        top_n=2,
    )

    assert len(top_prods) == 2
    # P2: 250.0 revenue, P1: 200.0 revenue
    assert top_prods[0].product_id == "P2"
    assert top_prods[0].revenue == 250.0
    assert top_prods[0].units_sold == 1
    assert top_prods[0].avg_price == 250.0

    assert top_prods[1].product_id == "P1"
    assert top_prods[1].revenue == 200.0
    assert top_prods[1].units_sold == 4
    assert top_prods[1].avg_price == 50.0
