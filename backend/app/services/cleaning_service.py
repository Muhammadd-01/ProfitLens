"""Data Cleaning and Transformation Pipeline.

Turn raw, messy business data into clean, standardized, model-ready datasets.
Executes deduplication, datetime standardization, numeric coercion, missing value
imputation, and outlier handling with a comprehensive audit trail.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset
from app.schemas.dataset import (
    CleaningAuditAction,
    CleaningStrategyConfig,
    CleaningSummary,
)
from app.utils.constants import DatasetStatus
from app.utils.file_processing import detect_encoding, detect_delimiter
from app.services.mapping_service import get_dataset_mapping_suggestions


def load_dataset_as_dataframe(file_path: str, file_type: str) -> pd.DataFrame:
    """Load raw dataset into pandas DataFrame with encoding and delimiter fallbacks."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_type == "xlsx" or file_path.endswith(".xlsx"):
        return pd.read_excel(file_path)

    # CSV reading with encoding detection
    encoding = detect_encoding(file_path)
    delimiter = detect_delimiter(file_path, encoding=encoding)
    
    try:
        return pd.read_csv(file_path, encoding=encoding, sep=delimiter, low_memory=False)
    except Exception:
        # Fallback to python engine with auto-separator
        return pd.read_csv(file_path, encoding="latin1", sep=None, engine="python")


def clean_numeric_series(series: pd.Series) -> pd.Series:
    """Strip currency symbols, commas, and percentage characters, then coerce to float."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    # String cleaning
    cleaned = (
        series.astype(str)
        .str.replace("$", "", regex=False)
        .str.replace("€", "", regex=False)
        .str.replace("£", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip()
    )
    # Replace empty strings and 'nan' with NaN
    cleaned = cleaned.replace(["nan", "None", "null", "N/A", "NA", ""], np.nan)
    return pd.to_numeric(cleaned, errors="coerce")


def winsorize_iqr(
    series: pd.Series,
    multiplier: float = 3.0,
    min_lower: Optional[float] = 0.0,
) -> Tuple[pd.Series, int, float, float]:
    """Winsorize extreme outliers using the Interquartile Range (IQR) fence rule.
    
    Returns:
        (clipped_series, outlier_count, lower_fence, upper_fence)
    """
    valid = series.dropna()
    if len(valid) < 10:
        return series, 0, 0.0, 0.0

    q25 = float(valid.quantile(0.25))
    q75 = float(valid.quantile(0.75))
    iqr = q75 - q25

    if iqr <= 0:
        return series, 0, q25, q75

    lower_fence = q25 - multiplier * iqr
    if min_lower is not None:
        lower_fence = max(min_lower, lower_fence)
    upper_fence = q75 + multiplier * iqr

    # Identify outliers
    outliers = (series < lower_fence) | (series > upper_fence)
    outlier_count = int(outliers.sum())

    clipped = series.clip(lower=lower_fence, upper=upper_fence)
    return clipped, outlier_count, lower_fence, upper_fence


def execute_cleaning_pipeline(
    df: pd.DataFrame,
    mappings: Dict[str, Optional[str]],
    config: CleaningStrategyConfig,
) -> Tuple[pd.DataFrame, List[CleaningAuditAction], int, int]:
    """Execute end-to-end data cleaning and transformation pipeline.
    
    Returns:
        (cleaned_df, audit_actions, original_missing_cells, cleaned_missing_cells)
    """
    actions: List[CleaningAuditAction] = []
    original_missing_cells = int(df.isna().sum().sum())
    initial_rows = len(df)

    # 1. Exact Row Deduplication
    if config.handle_duplicates:
        exact_dupes = int(df.duplicated().sum())
        if exact_dupes > 0:
            df = df.drop_duplicates().reset_index(drop=True)
            actions.append(
                CleaningAuditAction(
                    action_type="deduplication",
                    column=None,
                    description=f"Removed {exact_dupes:,} exact duplicate rows",
                    count_affected=exact_dupes,
                )
            )

    # Build reverse mapping: dataset_col -> canonical_field
    col_to_canonical = {col: canon for canon, col in mappings.items() if col and col in df.columns}

    # 2. Key-based Deduplication (Line-item vs Order-level deduplication)
    order_id_col = mappings.get("order_id")
    product_id_col = mappings.get("product_id")
    if config.handle_duplicates and order_id_col and order_id_col in df.columns:
        if product_id_col and product_id_col in df.columns:
            # Line-item level: duplicate order_id + product_id
            key_dupes = int(df.duplicated(subset=[order_id_col, product_id_col]).sum())
            if key_dupes > 0:
                df = df.drop_duplicates(subset=[order_id_col, product_id_col], keep="first").reset_index(drop=True)
                actions.append(
                    CleaningAuditAction(
                        action_type="deduplication",
                        column=order_id_col,
                        description=f"Removed {key_dupes:,} duplicate item rows sharing identical ({order_id_col}, {product_id_col})",
                        count_affected=key_dupes,
                    )
                )
        else:
            # Check for pure order_id duplicates
            key_dupes = int(df.duplicated(subset=[order_id_col]).sum())
            # Only drop if the duplicate count is very small (< 2% of data) indicating unintended duplicates,
            # rather than intentional order line items
            if 0 < key_dupes < (0.02 * len(df)):
                df = df.drop_duplicates(subset=[order_id_col], keep="first").reset_index(drop=True)
                actions.append(
                    CleaningAuditAction(
                        action_type="deduplication",
                        column=order_id_col,
                        description=f"Removed {key_dupes:,} duplicate order rows with identical order ID",
                        count_affected=key_dupes,
                    )
                )

    # 3. Datetime Normalization
    date_col = mappings.get("order_date")
    if date_col and date_col in df.columns:
        original_null_dates = int(df[date_col].isna().sum())
        converted_dates = pd.to_datetime(df[date_col], errors="coerce", utc=True)
        failed_dates = int(converted_dates.isna().sum()) - original_null_dates
        
        # If there are rows with unparseable or null dates in transaction log, drop or fill
        if failed_dates > 0:
            actions.append(
                CleaningAuditAction(
                    action_type="datetime_normalization",
                    column=date_col,
                    description=f"Coerced {failed_dates:,} corrupted/unparseable date strings to NaT",
                    count_affected=failed_dates,
                )
            )

        # Standardize format to ISO string (YYYY-MM-DD HH:MM:SS)
        valid_mask = converted_dates.notna()
        df.loc[valid_mask, date_col] = converted_dates[valid_mask].dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # Drop rows with null dates if they are < 5% of dataset (time series cannot function without date)
        null_date_count = int(df[date_col].isna().sum())
        if 0 < null_date_count < (0.05 * len(df)):
            df = df.dropna(subset=[date_col]).reset_index(drop=True)
            actions.append(
                CleaningAuditAction(
                    action_type="datetime_normalization",
                    column=date_col,
                    description=f"Dropped {null_date_count:,} rows with missing or unparseable transaction dates",
                    count_affected=null_date_count,
                )
            )
        else:
            actions.append(
                CleaningAuditAction(
                    action_type="datetime_normalization",
                    column=date_col,
                    description=f"Standardized {valid_mask.sum():,} transaction dates to ISO-8601 UTC format",
                    count_affected=int(valid_mask.sum()),
                )
            )

    # 4. Identifier & Text Columns Standardisation
    id_canonical_fields = ["customer_id", "product_id", "order_id"]
    for canon in id_canonical_fields:
        col = mappings.get(canon)
        if col and col in df.columns:
            # Strip whitespace
            df[col] = df[col].astype(str).str.strip()
            # Replace 'nan' or empty with placeholder
            missing_ids = df[col].isin(["nan", "None", "", "null", "N/A"])
            missing_id_count = int(missing_ids.sum())
            if missing_id_count > 0:
                fallback_val = f"UNKNOWN_{canon.upper()}"
                df.loc[missing_ids, col] = fallback_val
                actions.append(
                    CleaningAuditAction(
                        action_type="missing_imputation",
                        column=col,
                        description=f"Assigned '{fallback_val}' to {missing_id_count:,} blank identifier records",
                        count_affected=missing_id_count,
                    )
                )

    # 5. Numeric Columns Coercion, Non-Negativity & Imputation
    numeric_canonicals = ["revenue", "quantity", "price", "cost", "discount"]
    for canon in numeric_canonicals:
        col = mappings.get(canon)
        if col and col in df.columns:
            # Coerce to float
            df[col] = clean_numeric_series(df[col])

            # Handle negative values for revenue, quantity, price
            if config.clip_negative_values and canon in ["revenue", "quantity", "price"]:
                neg_count = int((df[col] < 0).sum())
                if neg_count > 0:
                    df[col] = df[col].clip(lower=0.0)
                    actions.append(
                        CleaningAuditAction(
                            action_type="type_coercion",
                            column=col,
                            description=f"Clipped {neg_count:,} negative values in {canon} ({col}) to 0.0",
                            count_affected=neg_count,
                        )
                    )

            # Impute missing numeric values
            missing_count = int(df[col].isna().sum())
            if missing_count > 0:
                if config.impute_missing_numeric == "median":
                    impute_val = float(df[col].median()) if df[col].notna().any() else 0.0
                    df[col] = df[col].fillna(impute_val)
                    actions.append(
                        CleaningAuditAction(
                            action_type="missing_imputation",
                            column=col,
                            description=f"Imputed {missing_count:,} missing values in {canon} with robust median ({impute_val:.2f})",
                            count_affected=missing_count,
                        )
                    )
                elif config.impute_missing_numeric == "mean":
                    impute_val = float(df[col].mean()) if df[col].notna().any() else 0.0
                    df[col] = df[col].fillna(impute_val)
                    actions.append(
                        CleaningAuditAction(
                            action_type="missing_imputation",
                            column=col,
                            description=f"Imputed {missing_count:,} missing values in {canon} with mean ({impute_val:.2f})",
                            count_affected=missing_count,
                        )
                    )
                elif config.impute_missing_numeric == "zero":
                    df[col] = df[col].fillna(0.0)
                    actions.append(
                        CleaningAuditAction(
                            action_type="missing_imputation",
                            column=col,
                            description=f"Imputed {missing_count:,} missing values in {canon} with zero (0.0)",
                            count_affected=missing_count,
                        )
                    )
                elif config.impute_missing_numeric == "drop":
                    df = df.dropna(subset=[col]).reset_index(drop=True)
                    actions.append(
                        CleaningAuditAction(
                            action_type="missing_imputation",
                            column=col,
                            description=f"Dropped {missing_count:,} rows with missing values in {canon}",
                            count_affected=missing_count,
                        )
                    )

            # Outlier Handling (Winsorization) on revenue & price
            if config.clip_outliers and canon in ["revenue", "price"]:
                clipped, out_cnt, low_f, up_f = winsorize_iqr(
                    df[col], multiplier=3.0, min_lower=0.0
                )
                if out_cnt > 0:
                    df[col] = clipped
                    actions.append(
                        CleaningAuditAction(
                            action_type="outlier_handling",
                            column=col,
                            description=f"Winsorized {out_cnt:,} extreme outlier values in {canon} outside fence [${low_f:.2f}, ${up_f:.2f}]",
                            count_affected=out_cnt,
                        )
                    )

    # 6. Categorical Columns Standardisation & Imputation
    categorical_canonicals = ["category", "region", "payment_method", "channel", "status"]
    for canon in categorical_canonicals:
        col = mappings.get(canon)
        if col and col in df.columns:
            # Strip whitespace and replace empty
            df[col] = df[col].astype(str).str.strip()
            df.loc[df[col].isin(["nan", "None", "", "null", "N/A"]), col] = np.nan

            missing_count = int(df[col].isna().sum())
            if missing_count > 0:
                if config.impute_missing_categorical == "mode" and df[col].notna().any():
                    mode_val = str(df[col].mode()[0])
                    df[col] = df[col].fillna(mode_val)
                    actions.append(
                        CleaningAuditAction(
                            action_type="missing_imputation",
                            column=col,
                            description=f"Imputed {missing_count:,} missing categorical values in {canon} with mode '{mode_val}'",
                            count_affected=missing_count,
                        )
                    )
                else:
                    fallback_cat = f"Unknown"
                    df[col] = df[col].fillna(fallback_cat)
                    actions.append(
                        CleaningAuditAction(
                            action_type="missing_imputation",
                            column=col,
                            description=f"Imputed {missing_count:,} missing categorical values in {canon} with '{fallback_cat}'",
                            count_affected=missing_count,
                        )
                    )

    cleaned_missing_cells = int(df.isna().sum().sum())
    return df, actions, original_missing_cells, cleaned_missing_cells


async def clean_dataset(
    dataset_id: str,
    organization_id: str,
    config: Optional[CleaningStrategyConfig] = None,
    db: Optional[AsyncSession] = None,
) -> CleaningSummary:
    """Execute cleaning pipeline for a dataset and persist cleaned dataset file."""
    if config is None:
        config = CleaningStrategyConfig()

    if db is None:
        raise ValueError("Database session required")

    result = await db.execute(
        select(Dataset).where(
            Dataset.id == uuid.UUID(dataset_id),
            Dataset.organization_id == uuid.UUID(organization_id),
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise ValueError(f"Dataset {dataset_id} not found")

    # Load dataframe
    df = load_dataset_as_dataframe(dataset.file_path, dataset.file_type)
    original_rows = len(df)

    # Get column mappings
    mappings = dataset.column_mappings or {}
    if not mappings:
        # Generate automatic mappings if not yet manually saved
        mapping_resp = await get_dataset_mapping_suggestions(dataset_id, organization_id, db)
        mappings = {m.canonical_field: m.mapped_column for m in mapping_resp.mappings if m.mapped_column}

    # Update dataset status to cleaning
    dataset.status = DatasetStatus.CLEANING.value
    await db.commit()

    try:
        # Run cleaning pipeline
        cleaned_df, actions, orig_missing, clean_missing = execute_cleaning_pipeline(
            df=df,
            mappings=mappings,
            config=config,
        )

        cleaned_rows = len(cleaned_df)
        rows_removed = original_rows - cleaned_rows

        # Save cleaned file
        base_dir = os.path.dirname(dataset.file_path)
        cleaned_file_name = f"{dataset.id}_cleaned.csv"
        cleaned_file_path = os.path.join(base_dir, cleaned_file_name)
        cleaned_df.to_csv(cleaned_file_path, index=False)

        cleaned_at = datetime.utcnow().isoformat()

        summary_dict = {
            "dataset_id": str(dataset.id),
            "original_rows": original_rows,
            "cleaned_rows": cleaned_rows,
            "rows_removed": rows_removed,
            "original_missing_cells": orig_missing,
            "cleaned_missing_cells": clean_missing,
            "cleaned_file_path": cleaned_file_path,
            "actions": [a.model_dump() for a in actions],
            "cleaned_at": cleaned_at,
        }

        # Update dataset record
        col_meta = dataset.column_metadata or {}
        col_meta["cleaning_summary"] = summary_dict
        col_meta["cleaned_file_path"] = cleaned_file_path
        dataset.column_metadata = col_meta
        dataset.row_count = cleaned_rows
        dataset.status = DatasetStatus.READY.value
        dataset.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(dataset)

        return CleaningSummary(
            dataset_id=str(dataset.id),
            original_rows=original_rows,
            cleaned_rows=cleaned_rows,
            rows_removed=rows_removed,
            original_missing_cells=orig_missing,
            cleaned_missing_cells=clean_missing,
            cleaned_file_path=cleaned_file_path,
            actions=actions,
            cleaned_at=cleaned_at,
        )

    except Exception as e:
        dataset.status = DatasetStatus.ERROR.value
        dataset.error_message = f"Cleaning error: {str(e)}"
        await db.commit()
        raise e
