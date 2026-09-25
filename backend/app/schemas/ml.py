"""Pydantic schemas for Machine Learning modules (Customer Segmentation, Churn, Forecasting, Anomaly Detection)."""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class SegmentProfile(BaseModel):
    """Detailed profile of a discovered customer behavioral segment."""
    cluster_id: int
    label: str
    description: str
    customer_count: int
    percentage: float
    avg_recency: float
    avg_frequency: float
    avg_monetary: float
    avg_order_value: float
    color: str
    strategy_recommendation: str


class ElbowPoint(BaseModel):
    """Evaluation metrics for a specific cluster count k."""
    k: int
    inertia: float
    silhouette: float


class PCAPoint(BaseModel):
    """2D projection coordinate for interactive scatter plot."""
    customer_id: str
    x: float
    y: float
    cluster_id: int
    label: str
    monetary: float
    frequency: int
    recency: int


class SegmentationTrainRequest(BaseModel):
    """Request payload for training or refitting customer segmentation."""
    k: Optional[int] = None  # None = auto-select optimal k using silhouette score


class SegmentationTrainResponse(BaseModel):
    """Complete response returned after fitting customer segmentation model."""
    dataset_id: str
    optimal_k: int
    silhouette_score: float
    total_customers: int
    pca_variance_explained: float
    segments: List[SegmentProfile]
    elbow_curve: List[ElbowPoint]
    pca_scatter: List[PCAPoint]
    trained_at: str


class ConfusionMatrix(BaseModel):
    """Classification confusion matrix counts."""
    tp: int
    fp: int
    tn: int
    fn: int


class ChurnMetrics(BaseModel):
    """Evaluation metrics for customer churn prediction model."""
    roc_auc: float
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    confusion_matrix: ConfusionMatrix


class FeatureImportanceItem(BaseModel):
    """Relative importance of an engineered feature in driving churn prediction."""
    feature_name: str
    importance_score: float
    description: str


class ChurnRiskDistribution(BaseModel):
    """Aggregated population counts across churn risk tiers."""
    low_count: int
    medium_count: int
    high_count: int
    critical_count: int
    low_pct: float
    medium_pct: float
    high_pct: float
    critical_pct: float


class CustomerChurnRisk(BaseModel):
    """Individual customer churn prediction with risk stratification and retention advice."""
    customer_id: str
    churn_risk_score: float
    churn_risk_level: str  # "low", "medium", "high", "critical"
    monetary_total: float
    frequency: int
    recency_days: int
    top_risk_factors: List[str]
    recommended_action: str


class ChurnTrainRequest(BaseModel):
    """Request payload for training or retraining churn classification models."""
    model_config = {"protected_namespaces": ()}
    model_type: Optional[str] = "auto"  # "auto", "random_forest", "logistic_regression"
    inactivity_threshold_days: Optional[int] = None


class ChurnOverviewResponse(BaseModel):
    """High-level summary of model performance, risk distribution, and revenue at risk."""
    model_config = {"protected_namespaces": ()}
    dataset_id: str
    model_type_used: str
    metrics: ChurnMetrics
    risk_distribution: ChurnRiskDistribution
    top_features: List[FeatureImportanceItem]
    total_customers_evaluated: int
    total_revenue_at_risk: float
    trained_at: str


class ChurnCustomerListResponse(BaseModel):
    """Paginated list of individual customer churn scores and risk factors."""
    dataset_id: str
    customers: List[CustomerChurnRisk]
    total: int
    page: int
    page_size: int


class ForecastDataPoint(BaseModel):
    """A single daily time-series point with historical or predicted revenue and confidence bounds."""
    date: str
    actual: Optional[float] = None
    predicted: float
    lower_bound: float
    upper_bound: float
    is_forecast: bool


class ForecastMetrics(BaseModel):
    """Goodness-of-fit and out-of-sample forecast accuracy metrics."""
    mae: float
    rmse: float
    mape: Optional[float] = None
    r2_score: Optional[float] = None


class SeasonalityDecomposition(BaseModel):
    """Detected seasonal patterns and growth trajectory."""
    trend_direction: str  # "Growing", "Stable", "Declining"
    growth_rate_pct: float
    seasonality_detected: bool
    seasonality_period_days: Optional[int] = None
    peak_day_of_week: Optional[str] = None
    trough_day_of_week: Optional[str] = None


class ForecastTrainRequest(BaseModel):
    """Payload to trigger forecasting model execution."""
    model_config = {"protected_namespaces": ()}
    model_type: Optional[str] = "auto"  # "auto", "holt_winters", "arima", "linear_trend"
    horizon_days: Optional[int] = 30
    confidence_level: Optional[float] = 0.95


class ForecastResponse(BaseModel):
    """Comprehensive time-series forecast output."""
    model_config = {"protected_namespaces": ()}
    dataset_id: str
    model_name: str
    horizon_days: int
    confidence_level: float
    metrics: ForecastMetrics
    seasonality: SeasonalityDecomposition
    historical_points: int
    forecast_points: int
    series: List[ForecastDataPoint]
    projected_total_revenue: float
    projected_growth_pct: Optional[float] = None
    generated_at: str


class AnomalyItem(BaseModel):
    """An individual detected transaction anomaly with explanation and review state."""
    id: str
    order_id: str
    customer_id: Optional[str] = None
    order_date: str
    amount: float
    anomaly_score: float
    severity: str  # "critical", "high", "medium", "low"
    reason: str
    details: Dict[str, Any]
    is_reviewed: bool
    review_status: str  # "pending", "confirmed_fraud", "operational_glitch", "false_positive"
    detected_at: str


class AnomalySeverityDistribution(BaseModel):
    """Aggregate statistics for detected transaction outliers."""
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    total_anomalies: int
    total_flagged_revenue: float
    reviewed_count: int


class AnomalyDetectRequest(BaseModel):
    """Payload to trigger anomaly detection scan."""
    contamination: Optional[float] = 0.02
    sensitivity: Optional[str] = "balanced"  # "conservative", "balanced", "aggressive"


class AnomalyOverviewResponse(BaseModel):
    """Full payload for transaction anomaly dashboard."""
    dataset_id: str
    total_orders_scanned: int
    distribution: AnomalySeverityDistribution
    anomalies: List[AnomalyItem]
    detected_at: str


class AnomalyReviewRequest(BaseModel):
    """Operator review action for a flagged anomaly."""
    review_status: str  # "confirmed_fraud", "operational_glitch", "false_positive"
    notes: Optional[str] = None


class SentimentReviewItem(BaseModel):
    """Analyzed customer review record with sentiment scores and aspect classification."""
    id: str
    customer_id: Optional[str] = None
    product_id: Optional[str] = None
    order_id: Optional[str] = None
    order_date: Optional[str] = None
    rating: Optional[float] = None
    review_text: str
    sentiment_label: str  # "positive", "neutral", "negative"
    sentiment_score: float  # compound score in [-1.0, 1.0]
    aspect_tags: List[str]


class AspectSentiment(BaseModel):
    """Aspect-based breakdown of customer sentiment (Quality, Shipping, Service, Price)."""
    aspect: str
    total_mentions: int
    positive_mentions: int
    neutral_mentions: int
    negative_mentions: int
    avg_sentiment_score: float
    sentiment_label: str
    top_terms: List[str]


class KeywordItem(BaseModel):
    """High-salience TF-IDF keyword extracted from reviews."""
    keyword: str
    frequency: int
    tfidf_score: float
    sentiment: str  # "positive", "negative", "neutral"


class SentimentDistribution(BaseModel):
    """Overall review sentiment distribution and Net Sentiment Score."""
    positive_count: int
    neutral_count: int
    negative_count: int
    total_reviews: int
    avg_compound_score: float
    net_sentiment_score: float  # (% positive - % negative) in [-100.0, 100.0]
    avg_rating: Optional[float] = None


class SentimentOverviewResponse(BaseModel):
    """Complete NLP sentiment intelligence packet."""
    dataset_id: str
    distribution: SentimentDistribution
    aspects: List[AspectSentiment]
    top_keywords: List[KeywordItem]
    recent_reviews: List[SentimentReviewItem]
    analyzed_at: str




