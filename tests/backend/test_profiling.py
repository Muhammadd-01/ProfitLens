from __future__ import annotations

import os
import pandas as pd
import pytest
from app.services.profiling_service import (
    infer_column_type,
    match_potential_role,
    profile_dataframe,
)

DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../data/synthetic")
)


def test_infer_column_type():
    """Verify semantic type inference on various column types."""
    # Numeric
    num_series = pd.Series([10, 20, 30, 40, 50])
    assert infer_column_type(num_series) == "numeric"

    currency_series = pd.Series(["$12.50", "$99.00", "$4.20", "$150.00"])
    assert infer_column_type(currency_series) == "numeric"

    # Boolean
    bool_series = pd.Series(["yes", "no", "yes", "yes", "no"])
    assert infer_column_type(bool_series) == "boolean"

    # Datetime
    date_series = pd.Series(["2024-01-15", "2024-02-20", "2024-03-01"])
    assert infer_column_type(date_series) == "datetime"

    # Categorical
    cat_series = pd.Series(["North", "South", "East", "West"] * 25)
    assert infer_column_type(cat_series) == "categorical"


def test_match_potential_role():
    """Verify domain pattern matching for business columns."""
    assert match_potential_role("Customer_ID", "identifier") == "customer_id"
    assert match_potential_role("total_revenue", "numeric") == "revenue"
    assert match_potential_role("order_date", "datetime") == "order_date"
    assert match_potential_role("unit_price", "numeric") == "revenue" or match_potential_role("unit_price", "numeric") is not None


def test_profile_dataframe_synthetic_customers():
    """Verify profiling on synthetic customers.csv (includes simulated nulls)."""
    path = os.path.join(DATA_DIR, "customers.csv")
    df = pd.read_csv(path)

    report = profile_dataframe(df, dataset_id="test-123", dataset_name="customers.csv")

    assert report.row_count >= 9000
    assert report.column_count >= 5
    assert report.quality_score > 70.0  # Synthetic data has realistic ~3-5% missing emails
    assert report.quality_grade in ["Excellent", "Good"]

    # Verify column profiles
    col_names = [c.name for c in report.columns]
    assert "customer_id" in col_names
    assert "name" in col_names
    assert "email" in col_names

    # Check that human-language issues are generated
    assert len(report.issues) > 0
    issue_descriptions = [i.description for i in report.issues]
    assert any("missing" in desc.lower() for desc in issue_descriptions)


def test_profile_empty_dataframe():
    """Verify quality score on empty dataframe."""
    df_empty = pd.DataFrame()
    report = profile_dataframe(df_empty, dataset_id="empty-1", dataset_name="empty.csv")
    assert report.quality_score == 0.0
    assert report.quality_grade == "Poor"
    assert len(report.issues) == 1
    assert report.issues[0].issue_type == "empty_dataset"
