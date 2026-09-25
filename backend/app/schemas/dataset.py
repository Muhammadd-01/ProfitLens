"""Pydantic schemas for datasets, file uploads, data profiling, and column mapping."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DatasetUploadResponse(BaseModel):
    """Response returned immediately after file upload and initial inspection."""
    id: str
    name: str
    file_type: str
    file_size_bytes: int
    row_count: int
    column_count: int
    columns: List[str]
    detected_encoding: Optional[str] = None
    detected_delimiter: Optional[str] = None
    status: str
    created_at: str


class ColumnProfile(BaseModel):
    """Detailed statistical and semantic profile of a single column."""
    name: str
    inferred_type: str  # numeric, categorical, datetime, boolean, identifier, text
    missing_count: int
    missing_percentage: float
    unique_count: int
    uniqueness_ratio: float
    sample_values: List[str]
    potential_role: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    median_value: Optional[float] = None
    std_value: Optional[float] = None
    top_categories: Optional[List[Dict[str, Any]]] = None
    min_date: Optional[str] = None
    max_date: Optional[str] = None


class QualityIssueItem(BaseModel):
    """Human-readable explanation of a data quality problem."""
    column: Optional[str] = None
    issue_type: str
    severity: str    # critical, warning, info
    description: str
    recommendation: str


class DataQualityReport(BaseModel):
    """Complete data profiling and quality report."""
    dataset_id: str
    dataset_name: str
    row_count: int
    column_count: int
    duplicate_rows_count: int
    duplicate_rows_percentage: float
    total_missing_cells: int
    total_missing_percentage: float
    quality_score: float
    quality_grade: str
    columns: List[ColumnProfile]
    issues: List[QualityIssueItem]
    detected_roles: Dict[str, str]
    profiled_at: str


class ColumnMappingSuggestion(BaseModel):
    """Single suggested column mapping with confidence score."""
    canonical_field: str       # e.g. 'revenue'
    field_display_name: str    # e.g. 'Revenue / Sales Amount'
    is_required: bool
    description: str
    mapped_column: Optional[str] = None  # dataset column name
    confidence: float          # 0.0 to 1.0
    confidence_level: str      # 'high', 'medium', 'low', 'unmapped'
    matched_by: str            # 'exact_match', 'pattern_match', 'fuzzy_similarity'
    alternative_columns: List[str] = []


class ColumnMappingResponse(BaseModel):
    """List of all canonical fields with suggested mappings."""
    dataset_id: str
    mappings: List[ColumnMappingSuggestion]
    available_columns: List[str]


class SaveColumnMappingRequest(BaseModel):
    """User confirmed column mapping payload."""
    mappings: Dict[str, Optional[str]]  # canonical_field -> dataset_column_name


class ModuleReadiness(BaseModel):
    """Readiness status for a specific analytics module."""
    module: str
    is_ready: bool
    required_fields: List[str]
    missing_fields: List[str]
    message: str


class SchemaValidationResult(BaseModel):
    """Validation report indicating which analytics modules can run."""
    dataset_id: str
    is_valid_for_basic_analytics: bool
    is_valid_for_ml: bool
    module_readiness: List[ModuleReadiness]
    summary_message: str


class DatasetResponse(BaseModel):
    """Detailed dataset schema."""
    id: str
    organization_id: str
    uploaded_by: str
    name: str
    file_type: str
    file_size_bytes: Optional[int] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    data_quality_score: Optional[float] = None
    column_mappings: Optional[Dict[str, Any]] = None
    column_metadata: Optional[Dict[str, Any]] = None
    profiling_results: Optional[Dict[str, Any]] = None
    status: str
    error_message: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class DatasetListResponse(BaseModel):
    """List of datasets."""
    datasets: List[DatasetResponse]
    total: int


class CleaningAuditAction(BaseModel):
    """Individual data cleaning or transformation action recorded in audit log."""
    action_type: str  # deduplication, datetime_normalization, type_coercion, missing_imputation, outlier_handling
    column: Optional[str] = None
    description: str
    count_affected: int


class CleaningStrategyConfig(BaseModel):
    """Configurable options for data cleaning pipeline."""
    handle_duplicates: bool = True
    impute_missing_numeric: str = "median"  # median, mean, zero, drop
    impute_missing_categorical: str = "mode"  # mode, unknown, drop
    clip_outliers: bool = True
    clip_negative_values: bool = True


class CleaningSummary(BaseModel):
    """Summary of data cleaning execution and before/after stats."""
    dataset_id: str
    original_rows: int
    cleaned_rows: int
    rows_removed: int
    original_missing_cells: int
    cleaned_missing_cells: int
    cleaned_file_path: str
    actions: List[CleaningAuditAction]
    cleaned_at: str


class FeatureCatalogItem(BaseModel):
    """Metadata item in feature store catalog."""
    name: str
    feature_group: str
    data_type: str
    description: str
    downstream_model: str
    mean_value: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None


class CustomerFeatureSummary(BaseModel):
    """Summary of engineered customer-level features."""
    total_customers: int
    avg_recency_days: float
    avg_frequency: float
    avg_monetary_spend: float
    avg_order_value: float
    multi_order_customer_pct: float
    features_file_path: str
    sample_records: List[Dict[str, Any]]


class TimeSeriesFeatureSummary(BaseModel):
    """Summary of engineered time-series temporal features."""
    total_days: int
    start_date: str
    end_date: str
    avg_daily_revenue: float
    features_file_path: str
    sample_records: List[Dict[str, Any]]


class FeatureEngineeringResponse(BaseModel):
    """Complete response returned after running feature engineering."""
    dataset_id: str
    customer_summary: Optional[CustomerFeatureSummary] = None
    timeseries_summary: Optional[TimeSeriesFeatureSummary] = None
    catalog: List[FeatureCatalogItem]
    generated_at: str
