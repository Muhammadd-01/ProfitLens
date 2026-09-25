"""Report Generation & Export Schemas."""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    """Configuration for on-demand report compilation."""
    report_type: Literal[
        "executive_summary",
        "financial_audit",
        "risk_assessment",
        "catalog_intelligence",
    ] = Field(default="executive_summary", description="Type of report to compile")
    format: Literal["pdf", "csv"] = Field(
        default="pdf", description="Output document format"
    )
    title: Optional[str] = Field(
        default=None, description="Custom document title override"
    )
    include_churn: bool = Field(
        default=True, description="Whether to include customer churn analysis"
    )
    include_anomalies: bool = Field(
        default=True, description="Whether to include anomaly & fraud triage logs"
    )
    include_products: bool = Field(
        default=True, description="Whether to include BCG matrix product catalog"
    )
    include_sentiment: bool = Field(
        default=True, description="Whether to include customer sentiment ABSA review scores"
    )


class ReportMetadataItem(BaseModel):
    """Metadata tracking generated report files."""
    id: str
    dataset_id: str
    report_name: str
    report_type: str
    format: str
    file_path: str
    file_size_bytes: int
    status: str
    summary_kpis: Dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ReportListResponse(BaseModel):
    """List of generated corporate reports for a dataset."""
    dataset_id: str
    reports: List[ReportMetadataItem]
    total: int
