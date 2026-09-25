from __future__ import annotations

import csv
import os
import pytest

DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../data/synthetic")
)


def test_synthetic_files_exist():
    """Verify all 5 generated CSV files exist."""
    expected_files = [
        "products.csv",
        "customers.csv",
        "orders.csv",
        "reviews.csv",
        "business_data.csv",
    ]
    for filename in expected_files:
        path = os.path.join(DATA_DIR, filename)
        assert os.path.exists(path), f"Missing {filename}"
        assert os.path.getsize(path) > 0, f"File {filename} is empty"


def test_products_structure():
    """Verify products CSV structure and row count (~100 products)."""
    path = os.path.join(DATA_DIR, "products.csv")
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        assert "product_id" in headers
        assert "name" in headers
        assert "category" in headers
        assert "unit_price" in headers

        rows = list(reader)
        assert len(rows) >= 90
        categories = set(r["category"] for r in rows)
        assert len(categories) >= 5


def test_orders_structure_and_anomaly_presence():
    """Verify orders dataset contains required columns and realistic amounts."""
    path = os.path.join(DATA_DIR, "orders.csv")
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        assert "order_id" in headers
        assert "customer_id" in headers
        assert "product_id" in headers
        assert "order_date" in headers
        assert "amount" in headers

        count = 0
        total_revenue = 0.0
        max_amount = 0.0
        for r in reader:
            count += 1
            amt = float(r["amount"])
            total_revenue += amt
            if amt > max_amount:
                max_amount = amt

        assert count >= 45000, f"Expected ~50,000 orders, got {count}"
        assert total_revenue > 0
        # High value anomaly should exist
        assert max_amount > 1000, "Should have anomalous high-value transactions"
