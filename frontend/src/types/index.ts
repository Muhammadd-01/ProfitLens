// Auth types
export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  organization_id: string;
  is_active: boolean;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan: 'free' | 'pro' | 'business';
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
  organization: Organization;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  organization_name: string;
}

export interface DatasetUploadResponse {
  id: string;
  name: string;
  file_type: string;
  file_size_bytes: number;
  row_count: number;
  column_count: number;
  columns: string[];
  detected_encoding?: string | null;
  detected_delimiter?: string | null;
  status: string;
  created_at: string;
}

export interface Dataset {
  id: string;
  name: string;
  file_type: string;
  file_size_bytes: number;
  row_count: number | null;
  column_count: number | null;
  data_quality_score: number | null;
  column_mappings: Record<string, string> | null;
  column_metadata: ColumnMetadata | null;
  profiling_results: ProfilingResults | null;
  status: DatasetStatus;
  created_at: string;
}

export type DatasetStatus =
  | 'uploaded'
  | 'validating'
  | 'profiled'
  | 'mapping'
  | 'cleaning'
  | 'transforming'
  | 'engineering'
  | 'ready'
  | 'analyzing'
  | 'complete'
  | 'error';

export interface ColumnMetadata {
  columns: ColumnInfo[];
}

export interface ColumnInfo {
  name: string;
  dtype: string;
  missing_count: number;
  missing_pct: number;
  unique_count: number;
  sample_values: string[];
}

export interface ProfilingResults {
  row_count: number;
  column_count: number;
  missing_total_pct: number;
  duplicate_count: number;
  duplicate_pct: number;
  numeric_columns: string[];
  categorical_columns: string[];
  date_columns: string[];
  potential_id_columns: string[];
  quality_score: number;
  quality_issues: QualityIssue[];
}

export interface QualityIssue {
  column: string;
  issue: string;
  severity: 'low' | 'medium' | 'high';
  description: string;
}

export interface ColumnProfile {
  name: string;
  inferred_type: string;
  missing_count: number;
  missing_percentage: number;
  unique_count: number;
  uniqueness_ratio: number;
  sample_values: string[];
  potential_role?: string | null;
  min_value?: number | null;
  max_value?: number | null;
  mean_value?: number | null;
  median_value?: number | null;
  std_value?: number | null;
  top_categories?: Array<{ category: string; count: number; percentage: number }> | null;
  min_date?: string | null;
  max_date?: string | null;
}

export interface QualityIssueItem {
  column?: string | null;
  issue_type: string;
  severity: 'critical' | 'warning' | 'info';
  description: string;
  recommendation: string;
}

export interface DataQualityReport {
  dataset_id: string;
  dataset_name: string;
  row_count: number;
  column_count: number;
  duplicate_rows_count: number;
  duplicate_rows_percentage: number;
  total_missing_cells: number;
  total_missing_percentage: number;
  quality_score: number;
  quality_grade: 'Excellent' | 'Good' | 'Fair' | 'Poor';
  columns: ColumnProfile[];
  issues: QualityIssueItem[];
  detected_roles: Record<string, string>;
  profiled_at: string;
}

export interface ColumnMappingSuggestion {
  canonical_field: string;
  field_display_name: string;
  is_required: boolean;
  description: string;
  mapped_column?: string | null;
  confidence: number;
  confidence_level: 'high' | 'medium' | 'low' | 'unmapped';
  matched_by: string;
  alternative_columns: string[];
}

export interface ColumnMappingResponse {
  dataset_id: string;
  mappings: ColumnMappingSuggestion[];
  available_columns: string[];
}

export interface SaveColumnMappingRequest {
  mappings: Record<string, string | null>;
}

export interface ModuleReadiness {
  module: string;
  is_ready: boolean;
  required_fields: string[];
  missing_fields: string[];
  message: string;
}

export interface SchemaValidationResult {
  dataset_id: string;
  is_valid_for_basic_analytics: boolean;
  is_valid_for_ml: boolean;
  module_readiness: ModuleReadiness[];
  summary_message: string;
}

// Cleaning types
export interface CleaningAuditAction {
  action_type: string;
  column: string | null;
  description: string;
  count_affected: number;
}

export interface CleaningStrategyConfig {
  handle_duplicates: boolean;
  impute_missing_numeric: 'median' | 'mean' | 'zero' | 'drop';
  impute_missing_categorical: 'mode' | 'unknown' | 'drop';
  clip_outliers: boolean;
  clip_negative_values: boolean;
}

export interface CleaningSummary {
  dataset_id: string;
  original_rows: number;
  cleaned_rows: number;
  rows_removed: number;
  original_missing_cells: number;
  cleaned_missing_cells: number;
  cleaned_file_path: string;
  actions: CleaningAuditAction[];
  cleaned_at: string;
}

// Feature Engineering types
export interface FeatureCatalogItem {
  name: string;
  feature_group: string;
  data_type: string;
  description: string;
  downstream_model: string;
  mean_value?: number | null;
  min_value?: number | null;
  max_value?: number | null;
}

export interface CustomerFeatureSummary {
  total_customers: number;
  avg_recency_days: number;
  avg_frequency: number;
  avg_monetary_spend: number;
  avg_order_value: number;
  multi_order_customer_pct: number;
  features_file_path: string;
  sample_records: Record<string, any>[];
}

export interface TimeSeriesFeatureSummary {
  total_days: number;
  start_date: string;
  end_date: string;
  avg_daily_revenue: number;
  features_file_path: string;
  sample_records: Record<string, any>[];
}

export interface FeatureEngineeringResponse {
  dataset_id: string;
  customer_summary?: CustomerFeatureSummary | null;
  timeseries_summary?: TimeSeriesFeatureSummary | null;
  catalog: FeatureCatalogItem[];
  generated_at: string;
}

// Analytics types
export interface KPIData {
  total_revenue: number;
  total_orders: number;
  total_customers: number;
  avg_order_value: number;
  revenue_change_pct: number | null;
  orders_change_pct: number | null;
  customers_change_pct: number | null;
  aov_change_pct: number | null;
}

export interface RevenueTimeSeries {
  date: string;
  revenue: number;
  orders: number;
  cumulative_revenue?: number;
}

export interface CategoryRevenue {
  category: string;
  revenue: number;
  orders: number;
  percentage: number;
  cumulative_percentage?: number;
  is_pareto_80?: boolean;
}

export interface ProductPerformanceSummary {
  product_id: string;
  revenue: number;
  units_sold: number;
  avg_price: number;
  order_count: number;
  percentage_of_total: number;
}

export interface ObservationPeriod {
  start_date: string;
  end_date: string;
  total_days: number;
}

export interface ExecutiveDashboardSummary {
  dataset_id: string;
  kpis: KPIData;
  time_series_daily: RevenueTimeSeries[];
  time_series_monthly: RevenueTimeSeries[];
  categories: CategoryRevenue[];
  top_products: ProductPerformanceSummary[];
  observation_period: ObservationPeriod;
}

export interface ProductPerformance {
  id: string;
  name: string;
  category: string;
  revenue: number;
  units_sold: number;
  order_count: number;
  avg_price: number;
  growth_pct: number | null;
  performance_tier: string;
}

// Customer types
export interface SegmentProfile {
  cluster_id: number;
  label: string;
  description: string;
  customer_count: number;
  percentage: number;
  avg_recency: number;
  avg_frequency: number;
  avg_monetary: number;
  avg_order_value: number;
  color: string;
  strategy_recommendation: string;
}

export interface ElbowPoint {
  k: number;
  inertia: number;
  silhouette: number;
}

export interface PCAPoint {
  customer_id: string;
  x: number;
  y: number;
  cluster_id: number;
  label: string;
  monetary: number;
  frequency: number;
  recency: number;
}

export interface SegmentationTrainRequest {
  k?: number | null;
}

export interface SegmentationTrainResponse {
  dataset_id: string;
  optimal_k: number;
  silhouette_score: number;
  total_customers: number;
  pca_variance_explained: number;
  segments: SegmentProfile[];
  elbow_curve: ElbowPoint[];
  pca_scatter: PCAPoint[];
  trained_at: string;
}

export interface CustomerSegment {
  label: string;
  count: number;
  avg_recency: number;
  avg_frequency: number;
  avg_monetary: number;
  description: string;
}

export interface ConfusionMatrix {
  tp: number;
  fp: number;
  tn: number;
  fn: number;
}

export interface ChurnMetrics {
  roc_auc: number;
  precision: number;
  recall: number;
  f1_score: number;
  accuracy: number;
  confusion_matrix: ConfusionMatrix;
}

export interface FeatureImportanceItem {
  feature_name: string;
  importance_score: number;
  description: string;
}

export interface ChurnRiskDistribution {
  low_count: number;
  medium_count: number;
  high_count: number;
  critical_count: number;
  low_pct: number;
  medium_pct: number;
  high_pct: number;
  critical_pct: number;
}

export interface CustomerChurnRisk {
  customer_id: string;
  churn_risk_score: number;
  churn_risk_level: 'low' | 'medium' | 'high' | 'critical';
  monetary_total: number;
  frequency: number;
  recency_days: number;
  top_risk_factors: string[];
  recommended_action: string;
}

export interface ChurnTrainRequest {
  model_type?: 'auto' | 'random_forest' | 'logistic_regression';
  inactivity_threshold_days?: number | null;
}

export interface ChurnOverviewResponse {
  dataset_id: string;
  model_type_used: string;
  metrics: ChurnMetrics;
  risk_distribution: ChurnRiskDistribution;
  top_features: FeatureImportanceItem[];
  total_customers_evaluated: number;
  total_revenue_at_risk: number;
  trained_at: string;
}

export interface ChurnCustomerListResponse {
  dataset_id: string;
  customers: CustomerChurnRisk[];
  total: number;
  page: number;
  page_size: number;
}

export interface ChurnRiskCustomer {
  id: string;
  external_id: string;
  name: string | null;
  churn_risk_score: number;
  churn_risk_level: 'low' | 'medium' | 'high' | 'critical';
  total_spent: number;
  order_count: number;
  days_since_last_purchase: number;
  contributing_factors: string[];
}

// Forecast types
export interface ForecastDataPoint {
  date: string;
  actual: number | null;
  predicted: number;
  lower_bound: number;
  upper_bound: number;
  is_forecast: boolean;
}

export interface ForecastMetrics {
  mae: number;
  rmse: number;
  mape: number | null;
  r2_score: number | null;
}

export interface SeasonalityDecomposition {
  trend_direction: string;
  growth_rate_pct: number;
  seasonality_detected: boolean;
  seasonality_period_days?: number | null;
  peak_day_of_week?: string | null;
  trough_day_of_week?: string | null;
}

export interface ForecastTrainRequest {
  model_type?: 'auto' | 'holt_winters' | 'arima' | 'linear_trend';
  horizon_days?: number;
  confidence_level?: number;
}

export interface ForecastResponse {
  dataset_id: string;
  model_name: string;
  horizon_days: number;
  confidence_level: number;
  metrics: ForecastMetrics;
  seasonality: SeasonalityDecomposition;
  historical_points: number;
  forecast_points: number;
  series: ForecastDataPoint[];
  projected_total_revenue: number;
  projected_growth_pct: number | null;
  generated_at: string;
}

export interface ForecastPoint {
  date: string;
  actual: number | null;
  predicted: number;
  lower_bound: number;
  upper_bound: number;
}

export interface ForecastResult {
  forecast: ForecastPoint[];
  metrics: {
    mae: number;
    rmse: number;
    mape: number | null;
  };
  model_name: string;
  horizon_days: number;
}

// Anomaly types
export interface AnomalyItem {
  id: string;
  order_id: string;
  customer_id?: string | null;
  order_date: string;
  amount: number;
  anomaly_score: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
  reason: string;
  details: Record<string, any>;
  is_reviewed: boolean;
  review_status: 'pending' | 'confirmed_fraud' | 'operational_glitch' | 'false_positive';
  detected_at: string;
}

export interface AnomalySeverityDistribution {
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  total_anomalies: number;
  total_flagged_revenue: number;
  reviewed_count: number;
}

export interface AnomalyDetectRequest {
  contamination?: number;
  sensitivity?: 'conservative' | 'balanced' | 'aggressive';
}

export interface AnomalyOverviewResponse {
  dataset_id: string;
  total_orders_scanned: number;
  distribution: AnomalySeverityDistribution;
  anomalies: AnomalyItem[];
  detected_at: string;
}

export interface AnomalyReviewRequest {
  review_status: 'confirmed_fraud' | 'operational_glitch' | 'false_positive';
  notes?: string;
}

export interface AnomalyRecord {
  id: string;
  order_id: string;
  external_order_id: string | null;
  amount: number;
  anomaly_score: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  reason: string;
  details: Record<string, unknown>;
  order_date: string;
  is_reviewed: boolean;
}

// Product Intelligence & BCG Matrix types
export interface ProductBCGItem {
  product_id: string;
  product_name?: string | null;
  category?: string | null;
  revenue: number;
  units_sold: number;
  avg_price: number;
  order_count: number;
  relative_market_share: number;
  growth_rate_pct: number;
  bcg_category: 'star' | 'cash_cow' | 'question_mark' | 'dog';
  pareto_class: 'A' | 'B' | 'C';
  cumulative_revenue_pct: number;
  return_rate_pct?: number | null;
  recommendation: string;
}

export interface ProductParetoPoint {
  rank: number;
  product_id: string;
  product_name: string;
  revenue: number;
  cumulative_revenue: number;
  cumulative_percentage: number;
  is_in_top_80: boolean;
}

export interface ProductBCGDistribution {
  stars_count: number;
  cash_cows_count: number;
  question_marks_count: number;
  dogs_count: number;
  total_products: number;
  stars_revenue: number;
  cash_cows_revenue: number;
  question_marks_revenue: number;
  dogs_revenue: number;
}

export interface ProductIntelligenceResponse {
  dataset_id: string;
  total_products: number;
  total_revenue: number;
  total_units_sold: number;
  avg_product_revenue: number;
  top_performing_category?: string | null;
  bcg_distribution: ProductBCGDistribution;
  pareto_points: ProductParetoPoint[];
  products: ProductBCGItem[];
  generated_at: string;
}

// Sentiment & NLP types
export interface SentimentReviewItem {
  id: string;
  customer_id?: string | null;
  product_id?: string | null;
  order_id?: string | null;
  order_date?: string | null;
  rating?: number | null;
  review_text: string;
  sentiment_label: 'positive' | 'neutral' | 'negative';
  sentiment_score: number;
  aspect_tags: string[];
}

export interface AspectSentiment {
  aspect: string;
  total_mentions: number;
  positive_mentions: number;
  neutral_mentions: number;
  negative_mentions: number;
  avg_sentiment_score: number;
  sentiment_label: 'mostly_positive' | 'mixed' | 'mostly_negative';
  top_terms: string[];
}

export interface KeywordItem {
  keyword: string;
  frequency: number;
  tfidf_score: number;
  sentiment: 'positive' | 'negative' | 'neutral';
}

export interface SentimentDistribution {
  positive_count: number;
  neutral_count: number;
  negative_count: number;
  total_reviews: number;
  avg_compound_score: number;
  net_sentiment_score: number;
  avg_rating?: number | null;
}

export interface SentimentOverviewResponse {
  dataset_id: string;
  distribution: SentimentDistribution;
  aspects: AspectSentiment[];
  top_keywords: KeywordItem[];
  recent_reviews: SentimentReviewItem[];
  analyzed_at: string;
}

// Insight types
export interface InsightItem {
  id: string;
  category: 'revenue' | 'churn' | 'customers' | 'products' | 'anomalies' | 'forecast' | 'sentiment';
  title: string;
  description: string;
  severity: 'critical' | 'warning' | 'positive' | 'info';
  confidence: number;
  impact_score: number;
  supporting_data: Record<string, any>;
  metrics: Record<string, any>;
  recommended_action: string;
  is_dismissed: boolean;
  created_at: string;
}

export interface InsightSummaryCounts {
  critical_count: number;
  warning_count: number;
  positive_count: number;
  info_count: number;
  total_insights: number;
}

export interface InsightFeedResponse {
  dataset_id: string;
  summary: InsightSummaryCounts;
  insights: InsightItem[];
  generated_at: string;
}

export interface Insight {
  id: string;
  category: 'revenue' | 'customers' | 'products' | 'anomalies' | 'data_quality' | 'forecast' | 'churn' | 'sentiment';
  title: string;
  description: string;
  severity: 'info' | 'warning' | 'critical' | 'positive';
  confidence: number | null;
  supporting_data: Record<string, unknown>;
  metrics: Record<string, number>;
  created_at: string;
}

// Analysis Run
export interface AnalysisRun {
  id: string;
  analysis_type: string;
  status: 'pending' | 'running' | 'complete' | 'failed';
  progress_percent: number;
  current_step: string | null;
  model_metrics: Record<string, unknown> | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
}

// Reports types
export interface ReportMetadataItem {
  id: string;
  dataset_id: string;
  report_name: string;
  report_type: 'executive_summary' | 'financial_audit' | 'risk_assessment' | 'catalog_intelligence';
  format: 'pdf' | 'csv';
  file_path: string;
  file_size_bytes: number;
  status: string;
  summary_kpis: Record<string, any>;
  created_at: string;
}

export interface ReportGenerateRequest {
  report_type: 'executive_summary' | 'financial_audit' | 'risk_assessment' | 'catalog_intelligence';
  format: 'pdf' | 'csv';
  title?: string;
  include_churn: boolean;
  include_anomalies: boolean;
  include_products: boolean;
  include_sentiment: boolean;
}

export interface ReportListResponse {
  dataset_id: string;
  reports: ReportMetadataItem[];
  total: number;
}

