"""Unit tests for Data Cleaning and Transformation Pipeline."""

import pytest
import pandas as pd
import numpy as np

from app.services.cleaning_service import (
    clean_numeric_series,
    winsorize_iqr,
    execute_cleaning_pipeline,
)
from app.schemas.dataset import CleaningStrategyConfig


def test_clean_numeric_series():
    """Verify string currency symbols, commas, and missing representations are properly coerced."""
    raw = pd.Series(["$1,250.50", "€45.00", "£12.99", "15%", "  99.9  ", "N/A", "nan", None])
    cleaned = clean_numeric_series(raw)
    
    assert cleaned.iloc[0] == 1250.50
    assert cleaned.iloc[1] == 45.00
    assert cleaned.iloc[2] == 12.99
    assert cleaned.iloc[3] == 15.0
    assert cleaned.iloc[4] == 99.9
    assert pd.isna(cleaned.iloc[5])
    assert pd.isna(cleaned.iloc[6])
    assert pd.isna(cleaned.iloc[7])


def test_winsorize_iqr():
    """Verify extreme outliers outside IQR fences are clipped."""
    # Data with clear median around 50 and one massive outlier at 10,000
    data = pd.Series([45.0, 48.0, 50.0, 52.0, 51.0, 49.0, 53.0, 47.0, 50.0, 52.0, 10000.0])
    clipped, outlier_count, lower_fence, upper_fence = winsorize_iqr(data, multiplier=3.0)
    
    assert outlier_count == 1
    assert clipped.max() <= upper_fence
    assert clipped.max() < 1000.0


def test_execute_cleaning_pipeline_deduplication():
    """Verify exact duplicate rows are detected, removed, and logged."""
    data = {
        "order_id": ["ORD-1", "ORD-1", "ORD-2", "ORD-3"],
        "order_date": ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-03"],
        "revenue": ["$50.00", "$50.00", "$100.00", "$75.00"],
        "customer_id": ["C1", "C1", "C2", "C3"],
    }
    df = pd.DataFrame(data)
    mappings = {
        "order_id": "order_id",
        "order_date": "order_date",
        "revenue": "revenue",
        "customer_id": "customer_id",
    }
    config = CleaningStrategyConfig(handle_duplicates=True)
    cleaned_df, actions, orig_missing, clean_missing = execute_cleaning_pipeline(df, mappings, config)
    
    assert len(cleaned_df) == 3
    dedupe_actions = [a for a in actions if a.action_type == "deduplication"]
    assert len(dedupe_actions) >= 1
    assert dedupe_actions[0].count_affected == 1


def test_execute_cleaning_pipeline_numeric_and_dates():
    """Verify numeric strings, negative clipping, median imputation, and date standardization."""
    data = {
        "order_id": ["O1", "O2", "O3", "O4", "O5"],
        "order_date": ["2023-05-10 14:00:00", "2023/06/15", "2023-07-20", "2023-08-25", "2023-09-30"],
        "revenue": ["$100.00", "-25.00", None, "$200.00", "$300.00"],
        "category": ["Electronics", "Fashion", "Electronics", None, "Home"],
        "customer_id": ["C1", "C2", None, "C4", "C5"],
    }
    df = pd.DataFrame(data)
    mappings = {
        "order_id": "order_id",
        "order_date": "order_date",
        "revenue": "revenue",
        "category": "category",
        "customer_id": "customer_id",
    }
    config = CleaningStrategyConfig(
        handle_duplicates=True,
        clip_negative_values=True,
        impute_missing_numeric="median",
        impute_missing_categorical="mode",
    )
    cleaned_df, actions, orig_missing, clean_missing = execute_cleaning_pipeline(df, mappings, config)
    
    # 1. Negative revenue clipped to 0
    assert (cleaned_df["revenue"] >= 0).all()
    assert cleaned_df["revenue"].iloc[1] == 0.0

    # 2. Missing revenue imputed with median (median of [100, 0, 200, 300] = 150)
    assert cleaned_df["revenue"].iloc[2] == 150.0
    assert not cleaned_df["revenue"].isna().any()

    # 3. Missing category imputed with mode ("Electronics")
    assert cleaned_df["category"].iloc[3] == "Electronics"

    # 4. Missing customer ID imputed with fallback
    assert cleaned_df["customer_id"].iloc[2] == "UNKNOWN_CUSTOMER_ID"

    # 5. Check action log types
    action_types = {a.action_type for a in actions}
    assert "type_coercion" in action_types
    assert "missing_imputation" in action_types
    assert "datetime_normalization" in action_types
