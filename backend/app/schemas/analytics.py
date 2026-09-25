"""Pydantic schemas for Executive Business Intelligence and KPI Analytics."""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class KPIData(BaseModel):
    """Core high-level executive business KPIs with period-over-period comparisons."""
    total_revenue: float
    total_orders: int
    total_customers: int
    avg_order_value: float
    revenue_change_pct: Optional[float] = None
    orders_change_pct: Optional[float] = None
    customers_change_pct: Optional[float] = None
    aov_change_pct: Optional[float] = None


class RevenueTimeSeries(BaseModel):
    """Aggregated sales and order count for a specific date or month bucket."""
    date: str
    revenue: float
    orders: int
    cumulative_revenue: Optional[float] = None


class CategoryRevenue(BaseModel):
    """Revenue contribution breakdown per category with Pareto 80/20 indicator."""
    category: str
    revenue: float
    orders: int
    percentage: float
    cumulative_percentage: Optional[float] = None
    is_pareto_80: Optional[bool] = None


class ProductPerformanceSummary(BaseModel):
    """Aggregated sales performance per product."""
    product_id: str
    revenue: float
    units_sold: int
    avg_price: float
    order_count: int
    percentage_of_total: float


class ObservationPeriod(BaseModel):
    """Date span of observation dataset."""
    start_date: str
    end_date: str
    total_days: int


class ExecutiveDashboardSummary(BaseModel):
    """Complete executive BI overview payload."""
    dataset_id: str
    kpis: KPIData
    time_series_daily: List[RevenueTimeSeries]
    time_series_monthly: List[RevenueTimeSeries]
    categories: List[CategoryRevenue]
    top_products: List[ProductPerformanceSummary]
    observation_period: ObservationPeriod


class ProductBCGItem(BaseModel):
    """Individual product performance with BCG Growth-Share and Pareto classification."""
    product_id: str
    product_name: Optional[str] = None
    category: Optional[str] = None
    revenue: float
    units_sold: int
    avg_price: float
    order_count: int
    relative_market_share: float
    growth_rate_pct: float
    bcg_category: str  # "star", "cash_cow", "question_mark", "dog"
    pareto_class: str  # "A", "B", "C"
    cumulative_revenue_pct: float
    return_rate_pct: Optional[float] = None
    recommendation: str


class ProductParetoPoint(BaseModel):
    """Data point along the Pareto 80/20 cumulative revenue distribution."""
    rank: int
    product_id: str
    product_name: str
    revenue: float
    cumulative_revenue: float
    cumulative_percentage: float
    is_in_top_80: bool


class ProductBCGDistribution(BaseModel):
    """Quadrant breakdown of product catalog."""
    stars_count: int
    cash_cows_count: int
    question_marks_count: int
    dogs_count: int
    total_products: int
    stars_revenue: float
    cash_cows_revenue: float
    question_marks_revenue: float
    dogs_revenue: float


class ProductIntelligenceResponse(BaseModel):
    """Complete product intelligence and BCG matrix payload."""
    dataset_id: str
    total_products: int
    total_revenue: float
    total_units_sold: int
    avg_product_revenue: float
    top_performing_category: Optional[str] = None
    bcg_distribution: ProductBCGDistribution
    pareto_points: List[ProductParetoPoint]
    products: List[ProductBCGItem]
    generated_at: str

