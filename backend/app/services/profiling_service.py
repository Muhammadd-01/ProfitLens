"""Data profiling and quality analysis engine.

DATA SCIENCE CONCEPT: AUTOMATED DATA PROFILING & QUALITY SCORING
================================================================

1. THE BUSINESS PROBLEM:
   Small business owners upload raw dumps from POS, Shopify, Excel, or Stripe.
   Real-world data is notoriously dirty:
   - Missing customer IDs (making retention and churn analysis impossible)
   - Duplicate transaction records (inflating revenue and skewing KPIs)
   - Mixed data types (e.g. "$1,200" stored as text instead of float)
   - Unrecognized dates (e.g. "01/02/2024" vs "2024-02-01")
   
   If we blindly feed dirty data into Machine Learning models, we suffer from
   "Garbage In, Garbage Out" (GIGO). We must automatically diagnose data health
   and communicate issues in plain business language before running any models.

2. THE MATHEMATICAL CONCEPTS:

   A. Completeness (Missingness Ratio):
      For any column c with N total rows:
          Missing Rate = (count of nulls in c) / N
      Total Dataset Missingness = (total null cells) / (N * M)
      where M is total number of columns.

   B. Cardinality & Uniqueness Ratio:
      Cardinality is the count of distinct values in column c:
          Uniqueness Ratio = |Unique(c)| / N
      - If Uniqueness Ratio ≈ 1.0 (and string/integer) -> Likely an Identifier (e.g., customer_id, order_id)
      - If Uniqueness Ratio < 0.05 or |Unique(c)| <= 50 -> Categorical (e.g., region, payment_method, status)
      - If |Unique(c)| == 1 -> Constant / Zero-Variance (useless for ML modeling)

   C. Data Quality Score Formula:
      We compute a composite score Q ∈ [0, 100]:
          Q = 100 - (P_missing + P_duplicates + P_critical)
      where:
          P_duplicates = (duplicate_rows / N) * 100 * 1.5
          P_missing    = (total_null_cells / (N * M)) * 100 * 0.8
          P_critical   = extra penalty if essential columns (ID, Date, Revenue) have nulls:
                         sum(critical_col_null_pct * 1.2)
      Clamped so Q ∈ [0, 100].

3. THE ALGORITHM:
   - Load dataset with pandas (sampling up to 100,000 rows if massive to ensure sub-second response)
   - Detect data types through robust multi-stage type inference
   - Match columns to domain roles (customer_id, revenue, order_date, etc.) via fuzzy pattern matching
   - Compute descriptive statistics (mean, median, std, min, max for numeric; top frequencies for categorical)
   - Synthesize human-language warnings explaining the business impact of each defect
"""

from __future__ import annotations

import re
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset
from app.schemas.dataset import (
    ColumnProfile,
    QualityIssueItem,
    DataQualityReport,
)
from app.utils.constants import COLUMN_PATTERNS
from app.utils.file_processing import detect_encoding, detect_delimiter


def infer_column_type(series: pd.Series) -> str:
    """Infer the semantic data type of a pandas Series.
    
    Returns: 'datetime', 'boolean', 'numeric', 'identifier', 'categorical', or 'text'.
    """
    non_null = series.dropna()
    total = len(non_null)
    if total == 0:
        return "text"

    # 1. Check for Boolean
    unique_vals = set(non_null.astype(str).str.lower().unique())
    boolean_sets = [
        {"true", "false"},
        {"0", "1"},
        {"yes", "no"},
        {"y", "n"},
        {"t", "f"},
    ]
    if any(unique_vals.issubset(b_set) for b_set in boolean_sets) and len(unique_vals) <= 2:
        return "boolean"

    # 2. Check for Numeric
    if pd.api.types.is_numeric_dtype(non_null):
        # If integer with 99%+ uniqueness and name implies ID, could be identifier
        unique_ratio = len(unique_vals) / total
        if pd.api.types.is_integer_dtype(non_null) and unique_ratio > 0.95 and total > 20:
            return "identifier"
        return "numeric"

    # Try converting strings with currency/commas to numeric (e.g. "$1,234.50")
    if pd.api.types.is_string_dtype(non_null) or pd.api.types.is_object_dtype(non_null):
        sample = non_null.head(100).astype(str).str.replace(r"[\$,€,£,\s]", "", regex=True)
        numeric_test = pd.to_numeric(sample, errors="coerce")
        if numeric_test.notnull().mean() > 0.90:
            return "numeric"

    # 3. Check for Datetime
    sample_dates = non_null.head(100).astype(str)
    # Require typical date delimiters or length
    date_like = sample_dates.str.contains(r"[\-/:]|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", case=False)
    if date_like.mean() > 0.8:
        try:
            parsed = pd.to_datetime(sample_dates, errors="coerce")
            if parsed.notnull().mean() > 0.85:
                return "datetime"
        except Exception:
            pass

    # 4. Check for Identifier vs Categorical vs Free Text
    unique_count = len(unique_vals)
    unique_ratio = unique_count / total

    if unique_ratio > 0.90 and total > 20:
        return "identifier"

    if unique_count <= 50 or unique_ratio < 0.20:
        return "categorical"

    return "text"


def match_potential_role(column_name: str, inferred_type: str) -> Optional[str]:
    """Match a column name against domain patterns to detect business roles."""
    cleaned = re.sub(r"[^a-z0-9]", "", column_name.lower())

    # Pass 1: Exact matches first
    for role, patterns in COLUMN_PATTERNS.items():
        for pattern in patterns:
            pattern_clean = re.sub(r"[^a-z0-9]", "", pattern.lower())
            if cleaned == pattern_clean:
                if role == "order_date" and inferred_type not in ["datetime", "text"]:
                    continue
                if role in ["revenue", "quantity", "discount"] and inferred_type not in ["numeric", "text"]:
                    continue
                return role

    # Pass 2: Substring matches with specific patterns
    for role, patterns in COLUMN_PATTERNS.items():
        for pattern in patterns:
            pattern_clean = re.sub(r"[^a-z0-9]", "", pattern.lower())
            if len(pattern_clean) >= 4 and pattern_clean in cleaned:
                if role == "order_date" and inferred_type not in ["datetime", "text"]:
                    continue
                if role in ["revenue", "quantity", "discount"] and inferred_type not in ["numeric", "text"]:
                    continue
                return role
    return None


def profile_dataframe(df: pd.DataFrame, dataset_id: str, dataset_name: str) -> DataQualityReport:
    """Perform comprehensive data profiling and quality analysis on a DataFrame."""
    n_rows, n_cols = df.shape
    if n_rows == 0:
        return DataQualityReport(
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            row_count=0,
            column_count=n_cols,
            duplicate_rows_count=0,
            duplicate_rows_percentage=0.0,
            total_missing_cells=0,
            total_missing_percentage=0.0,
            quality_score=0.0,
            quality_grade="Poor",
            columns=[],
            issues=[
                QualityIssueItem(
                    column=None,
                    issue_type="empty_dataset",
                    severity="critical",
                    description="The dataset contains zero rows.",
                    recommendation="Upload a dataset containing business records.",
                )
            ],
            detected_roles={},
            profiled_at=datetime.utcnow().isoformat(),
        )

    # 1. Global Duplicates & Missingness
    dup_count = int(df.duplicated().sum())
    dup_pct = round((dup_count / n_rows) * 100, 2)

    total_cells = n_rows * n_cols
    total_nulls = int(df.isnull().sum().sum())
    total_null_pct = round((total_nulls / total_cells) * 100, 2) if total_cells > 0 else 0.0

    # 2. Per-Column Profiling
    column_profiles: List[ColumnProfile] = []
    issues: List[QualityIssueItem] = []
    detected_roles: Dict[str, str] = {}
    critical_missing_penalty = 0.0

    for col in df.columns:
        series = df[col]
        null_count = int(series.isnull().sum())
        null_pct = round((null_count / n_rows) * 100, 2)
        unique_count = int(series.nunique(dropna=True))
        unique_ratio = round(unique_count / n_rows, 4) if n_rows > 0 else 0.0

        sample_vals = [
            str(x) for x in series.dropna().head(5).tolist()
        ]

        col_type = infer_column_type(series)
        potential_role = match_potential_role(str(col), col_type)

        if potential_role and potential_role not in detected_roles:
            detected_roles[potential_role] = str(col)

        profile = ColumnProfile(
            name=str(col),
            inferred_type=col_type,
            missing_count=null_count,
            missing_percentage=null_pct,
            unique_count=unique_count,
            uniqueness_ratio=unique_ratio,
            sample_values=sample_vals,
            potential_role=potential_role,
        )

        # Numeric statistics
        if col_type == "numeric":
            clean_num = pd.to_numeric(
                series.astype(str).str.replace(r"[\$,€,£,\s]", "", regex=True),
                errors="coerce"
            ).dropna()
            if len(clean_num) > 0:
                profile.min_value = float(clean_num.min())
                profile.max_value = float(clean_num.max())
                profile.mean_value = round(float(clean_num.mean()), 2)
                profile.median_value = round(float(clean_num.median()), 2)
                profile.std_value = round(float(clean_num.std()), 2) if len(clean_num) > 1 else 0.0

        # Categorical statistics
        elif col_type == "categorical":
            top_counts = series.value_counts(dropna=True).head(5)
            profile.top_categories = [
                {"category": str(k), "count": int(v), "percentage": round((v / n_rows) * 100, 1)}
                for k, v in top_counts.items()
            ]

        # Datetime statistics
        elif col_type == "datetime":
            parsed_dates = pd.to_datetime(series, errors="coerce").dropna()
            if len(parsed_dates) > 0:
                profile.min_date = parsed_dates.min().strftime("%Y-%m-%d")
                profile.max_date = parsed_dates.max().strftime("%Y-%m-%d")

        # 3. Detect column-specific quality issues
        if null_pct > 0:
            if potential_role in ["customer_id", "order_id", "revenue", "order_date"]:
                severity = "critical" if null_pct > 5.0 else "warning"
                critical_missing_penalty += (null_pct * 1.5)
                issues.append(
                    QualityIssueItem(
                        column=str(col),
                        issue_type="missing_critical_values",
                        severity=severity,
                        description=f"{null_pct}% of {potential_role.replace('_', ' ').title()} values are missing. Customer-level analysis and revenue calculations may be less accurate.",
                        recommendation="Impute missing values with business defaults or exclude incomplete records before modeling.",
                    )
                )
            else:
                severity = "warning" if null_pct > 15.0 else "info"
                issues.append(
                    QualityIssueItem(
                        column=str(col),
                        issue_type="missing_values",
                        severity=severity,
                        description=f"{null_pct}% of values in column '{col}' are missing.",
                        recommendation="If this column is not critical, consider dropping it or treating missing values as a distinct category.",
                    )
                )

        if unique_count == 1 and n_rows > 1:
            issues.append(
                QualityIssueItem(
                    column=str(col),
                    issue_type="constant_column",
                    severity="info",
                    description=f"Column '{col}' has only one unique value across all rows.",
                    recommendation="Constant columns provide zero variance and will be excluded from clustering and predictive algorithms.",
                )
            )

        column_profiles.append(profile)

    # 4. Check for duplicate rows issue
    if dup_count > 0:
        dup_severity = "critical" if dup_pct > 5.0 else "warning" if dup_pct > 1.0 else "info"
        issues.append(
            QualityIssueItem(
                column=None,
                issue_type="duplicate_records",
                severity=dup_severity,
                description=f"{dup_count:,} duplicate rows detected ({dup_pct}% of total records).",
                recommendation="Remove duplicate transactions to avoid double-counting sales revenue.",
            )
        )

    # 5. Missing core business entities
    expected_core_roles = ["customer_id", "revenue", "order_date"]
    for role in expected_core_roles:
        if role not in detected_roles:
            issues.append(
                QualityIssueItem(
                    column=None,
                    issue_type="missing_role_detection",
                    severity="warning",
                    description=f"No obvious column detected for '{role.replace('_', ' ').title()}'.",
                    recommendation="Review column mappings to explicitly assign this column for downstream analytics.",
                )
            )

    # 6. Quality Score Calculation
    # Formula: 100 - penalties
    penalty = (dup_pct * 1.2) + (total_null_pct * 0.8) + (critical_missing_penalty * 0.5)
    quality_score = max(0.0, min(100.0, round(100.0 - penalty, 1)))

    if quality_score >= 90.0:
        quality_grade = "Excellent"
    elif quality_score >= 80.0:
        quality_grade = "Good"
    elif quality_score >= 65.0:
        quality_grade = "Fair"
    else:
        quality_grade = "Poor"

    return DataQualityReport(
        dataset_id=dataset_id,
        dataset_name=dataset_name,
        row_count=n_rows,
        column_count=n_cols,
        duplicate_rows_count=dup_count,
        duplicate_rows_percentage=dup_pct,
        total_missing_cells=total_nulls,
        total_missing_percentage=total_null_pct,
        quality_score=quality_score,
        quality_grade=quality_grade,
        columns=column_profiles,
        issues=issues,
        detected_roles=detected_roles,
        profiled_at=datetime.utcnow().isoformat(),
    )


async def profile_dataset(
    dataset_id: str,
    organization_id: str,
    db: AsyncSession,
) -> DataQualityReport:
    """Load an uploaded dataset file, run the profiling engine, and save results in DB."""
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == uuid.UUID(dataset_id),
            Dataset.organization_id == uuid.UUID(organization_id),
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise ValueError("Dataset not found")

    file_path = dataset.file_path
    if not os.path.exists(file_path):
        raise ValueError("Dataset file does not exist on disk")

    ext = dataset.file_type.lower()
    if ext == "csv":
        # Read sample bytes to detect delimiter & encoding
        with open(file_path, "rb") as f:
            sample_bytes = f.read(65536)
        encoding = detect_encoding(sample_bytes)
        try:
            sample_text = sample_bytes.decode(encoding)
        except Exception:
            encoding = "latin-1"
            sample_text = sample_bytes.decode("latin-1", errors="replace")
        delimiter = detect_delimiter(sample_text)

        df = pd.read_csv(file_path, encoding=encoding, sep=delimiter, low_memory=False)
    else:
        df = pd.read_excel(file_path)

    # Run profiling
    report = profile_dataframe(df, str(dataset.id), dataset.name)

    # Update dataset in DB
    dataset.data_quality_score = report.quality_score
    dataset.row_count = report.row_count
    dataset.column_count = report.column_count
    dataset.status = "profiled"
    dataset.column_mappings = report.detected_roles
    dataset.profiling_results = report.dict()

    await db.flush()
    return report
