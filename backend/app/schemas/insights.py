"""Pydantic schemas for Automated Executive Insights Engine."""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class InsightItem(BaseModel):
    """An individual narrative business insight with supporting metrics and actions."""
    id: str
    category: str  # "revenue", "churn", "customers", "products", "anomalies", "forecast", "sentiment"
    title: str
    description: str
    severity: str  # "critical", "warning", "positive", "info"
    confidence: float
    impact_score: float
    supporting_data: Dict[str, Any]
    metrics: Dict[str, Any]
    recommended_action: str
    is_dismissed: bool
    created_at: str


class InsightSummaryCounts(BaseModel):
    """Counts of insights stratified by severity level."""
    critical_count: int
    warning_count: int
    positive_count: int
    info_count: int
    total_insights: int


class InsightFeedResponse(BaseModel):
    """Comprehensive executive insight feed payload."""
    dataset_id: str
    summary: InsightSummaryCounts
    insights: List[InsightItem]
    generated_at: str


class InsightDismissRequest(BaseModel):
    """Request payload to dismiss or restore an insight."""
    dismissed: bool = True
