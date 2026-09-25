import { useState, useEffect } from 'react';
import {
  Layers,
  Users,
  TrendingUp,
  Clock,
  Sparkles,
  ArrowRight,
  RefreshCw,
  Table2,
  Calendar,
  DollarSign,
  Activity,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TableSkeleton } from '@/components/common/loading-skeleton';
import api from '@/lib/api';
import type { FeatureEngineeringResponse, FeatureCatalogItem } from '@/types';
import { useNavigate } from 'react-router-dom';

interface FeatureCatalogCardProps {
  datasetId: string;
  datasetName: string;
  onProceedToAnalytics?: () => void;
}

export function FeatureCatalogCard({
  datasetId,
  datasetName,
  onProceedToAnalytics,
}: FeatureCatalogCardProps) {
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [featureData, setFeatureData] = useState<FeatureEngineeringResponse | null>(null);
  const [activeView, setActiveView] = useState<'catalog' | 'customer' | 'timeseries'>('catalog');
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchFeatures();
  }, [datasetId]);

  const fetchFeatures = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<FeatureEngineeringResponse>(`/datasets/${datasetId}/features/summary`);
      setFeatureData(response.data);
    } catch {
      setFeatureData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateFeatures = async () => {
    setGenerating(true);
    setError(null);
    try {
      const response = await api.post<FeatureEngineeringResponse>(`/datasets/${datasetId}/features/generate`);
      setFeatureData(response.data);
    } catch (err: unknown) {
      const errorMsg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Feature generation failed. Ensure dataset has order dates, customer IDs, and revenue mapped.';
      setError(errorMsg);
    } finally {
      setGenerating(false);
    }
  };

  const getGroupBadgeClass = (group: string) => {
    switch (group) {
      case 'Customer RFM':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      case 'Customer Behavior':
        return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20';
      case 'Time-Series Target':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'Time-Series Lags':
        return 'bg-sky-500/10 text-sky-400 border-sky-500/20';
      case 'Time-Series Rolling':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'Calendar & Seasonality':
        return 'bg-pink-500/10 text-pink-400 border-pink-500/20';
      default:
        return 'bg-primary/10 text-primary border-primary/20';
    }
  };

  if (loading) {
    return <TableSkeleton rows={6} />;
  }

  return (
    <div className="space-y-6">
      {/* Control Banner */}
      <Card className="border-border bg-card">
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <Layers className="h-5 w-5 text-primary" />
                Feature Store & Analytical Encodings
              </CardTitle>
              <CardDescription>
                Automated customer-level RFM vectors, inter-arrival intervals, regularized daily lags, and cyclical trigonometric features
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                onClick={handleGenerateFeatures}
                disabled={generating}
                className="text-xs flex items-center gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${generating ? 'animate-spin' : ''}`} />
                {generating ? 'Computing Features...' : featureData ? 'Re-generate Features' : 'Generate Features'}
              </Button>
            </div>
          </div>
        </CardHeader>

        {error && (
          <CardContent className="pt-0">
            <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          </CardContent>
        )}
      </Card>

      {featureData ? (
        <div className="space-y-6">
          {/* Summary Metric Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="border-border bg-card">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-muted-foreground">Customer Entities</span>
                  <Users className="h-4 w-4 text-purple-400" />
                </div>
                <div className="text-2xl font-bold text-foreground">
                  {featureData.customer_summary
                    ? featureData.customer_summary.total_customers.toLocaleString()
                    : '—'}
                </div>
                <span className="text-[11px] text-muted-foreground mt-1 block">
                  {featureData.customer_summary
                    ? `${featureData.customer_summary.multi_order_customer_pct}% repeat buyers`
                    : 'Customer ID unmapped'}
                </span>
              </CardContent>
            </Card>

            <Card className="border-border bg-card">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-muted-foreground">Mean Customer Spend</span>
                  <DollarSign className="h-4 w-4 text-emerald-400" />
                </div>
                <div className="text-2xl font-bold text-foreground">
                  {featureData.customer_summary
                    ? `$${featureData.customer_summary.avg_monetary_spend.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                    : '—'}
                </div>
                <span className="text-[11px] text-muted-foreground mt-1 block">
                  {featureData.customer_summary
                    ? `AOV: $${featureData.customer_summary.avg_order_value.toFixed(2)}`
                    : 'Revenue unmapped'}
                </span>
              </CardContent>
            </Card>

            <Card className="border-border bg-card">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-muted-foreground">Time Horizon</span>
                  <Calendar className="h-4 w-4 text-sky-400" />
                </div>
                <div className="text-2xl font-bold text-foreground">
                  {featureData.timeseries_summary
                    ? `${featureData.timeseries_summary.total_days} Days`
                    : '—'}
                </div>
                <span className="text-[11px] text-muted-foreground mt-1 block truncate">
                  {featureData.timeseries_summary
                    ? `${featureData.timeseries_summary.start_date} to ${featureData.timeseries_summary.end_date}`
                    : 'Date unmapped'}
                </span>
              </CardContent>
            </Card>

            <Card className="border-border bg-card">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-muted-foreground">Engineered Features</span>
                  <Sparkles className="h-4 w-4 text-primary" />
                </div>
                <div className="text-2xl font-bold text-primary">
                  {featureData.catalog.length}
                </div>
                <span className="text-[11px] text-muted-foreground mt-1 block">
                  Stored in analytical tables
                </span>
              </CardContent>
            </Card>
          </div>

          {/* Sub Navigation */}
          <div className="flex items-center justify-between border-b border-border pb-2">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveView('catalog')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  activeView === 'catalog'
                    ? 'bg-secondary text-foreground font-semibold'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Feature Store Catalog ({featureData.catalog.length})
              </button>
              {featureData.customer_summary && (
                <button
                  onClick={() => setActiveView('customer')}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                    activeView === 'customer'
                      ? 'bg-secondary text-foreground font-semibold'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Customer RFM Matrix
                </button>
              )}
              {featureData.timeseries_summary && (
                <button
                  onClick={() => setActiveView('timeseries')}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                    activeView === 'timeseries'
                      ? 'bg-secondary text-foreground font-semibold'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Time-Series & Lags Matrix
                </button>
              )}
            </div>

            <Button
              size="sm"
              onClick={() => {
                if (onProceedToAnalytics) {
                  onProceedToAnalytics();
                } else {
                  navigate('/dashboard');
                }
              }}
              className="text-xs flex items-center gap-1.5 bg-primary text-primary-foreground"
            >
              Open Predictive Dashboard <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </div>

          {/* View 1: Catalog */}
          {activeView === 'catalog' && (
            <Card className="border-border bg-card">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold">Engineered Features Dictionary</CardTitle>
                <CardDescription className="text-xs">
                  Derived mathematical and temporal attributes fed directly into downstream models
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border bg-secondary/30 text-muted-foreground text-left">
                        <th className="p-3 font-semibold">Feature Name</th>
                        <th className="p-3 font-semibold">Group</th>
                        <th className="p-3 font-semibold">Type</th>
                        <th className="p-3 font-semibold">Target Model</th>
                        <th className="p-3 font-semibold">Summary (Mean / Min / Max)</th>
                        <th className="p-3 font-semibold">Description</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/50">
                      {featureData.catalog.map((f) => (
                        <tr key={f.name} className="hover:bg-secondary/20 transition-colors">
                          <td className="p-3 font-mono font-medium text-foreground">{f.name}</td>
                          <td className="p-3">
                            <Badge
                              variant="outline"
                              className={`text-[10px] uppercase font-semibold ${getGroupBadgeClass(f.feature_group)}`}
                            >
                              {f.feature_group}
                            </Badge>
                          </td>
                          <td className="p-3 font-mono text-muted-foreground uppercase">{f.data_type}</td>
                          <td className="p-3 text-muted-foreground">{f.downstream_model}</td>
                          <td className="p-3 font-mono text-muted-foreground">
                            {f.mean_value !== null && f.mean_value !== undefined
                              ? `μ: ${f.mean_value.toFixed(1)} [${f.min_value?.toFixed(1) ?? '—'}, ${f.max_value?.toFixed(1) ?? '—'}]`
                              : '—'}
                          </td>
                          <td className="p-3 text-muted-foreground max-w-xs">{f.description}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* View 2: Customer Preview */}
          {activeView === 'customer' && featureData.customer_summary && (
            <Card className="border-border bg-card">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-sm font-semibold">Customer Feature Vector Sample</CardTitle>
                    <CardDescription className="text-xs">
                      Pre-computed customer profile table ready for Churn Prediction and $K$-Means Segmentation
                    </CardDescription>
                  </div>
                  <Badge variant="outline" className="text-xs font-mono">
                    {featureData.customer_summary.total_customers.toLocaleString()} total profiles
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border bg-secondary/30 text-muted-foreground text-left">
                        <th className="p-3 font-semibold">Customer ID</th>
                        <th className="p-3 font-semibold">Recency (d)</th>
                        <th className="p-3 font-semibold">Frequency</th>
                        <th className="p-3 font-semibold">Monetary ($)</th>
                        <th className="p-3 font-semibold">AOV ($)</th>
                        <th className="p-3 font-semibold">Lifespan (d)</th>
                        <th className="p-3 font-semibold">Interval (d)</th>
                        <th className="p-3 font-semibold">RFM Score</th>
                        <th className="p-3 font-semibold">Category</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/50">
                      {featureData.customer_summary.sample_records.map((rec, i) => (
                        <tr key={i} className="hover:bg-secondary/20 transition-colors">
                          <td className="p-3 font-mono font-medium text-foreground">{rec.customer_id}</td>
                          <td className="p-3 text-foreground">{rec.recency_days}</td>
                          <td className="p-3 text-foreground">{rec.frequency}</td>
                          <td className="p-3 font-mono text-emerald-400">${rec.monetary_total}</td>
                          <td className="p-3 font-mono text-foreground">${rec.avg_order_value}</td>
                          <td className="p-3 text-muted-foreground">{rec.customer_lifespan_days}</td>
                          <td className="p-3 text-muted-foreground">{rec.purchase_interval_mean}</td>
                          <td className="p-3 font-mono font-semibold text-primary">{rec.rfm_composite}</td>
                          <td className="p-3 text-muted-foreground">{rec.preferred_category || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* View 3: Time Series Preview */}
          {activeView === 'timeseries' && featureData.timeseries_summary && (
            <Card className="border-border bg-card">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-sm font-semibold">Time Series & Lag Features Sample</CardTitle>
                    <CardDescription className="text-xs">
                      Daily regularized sequence with 7d lag, 7d/30d moving averages, and cyclical trigonometric seasonality
                    </CardDescription>
                  </div>
                  <Badge variant="outline" className="text-xs font-mono">
                    {featureData.timeseries_summary.total_days} continuous days
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border bg-secondary/30 text-muted-foreground text-left">
                        <th className="p-3 font-semibold">Date</th>
                        <th className="p-3 font-semibold">Revenue ($)</th>
                        <th className="p-3 font-semibold">Orders</th>
                        <th className="p-3 font-semibold">Lag 1d ($)</th>
                        <th className="p-3 font-semibold">Lag 7d ($)</th>
                        <th className="p-3 font-semibold">Rolling 7d Mean ($)</th>
                        <th className="p-3 font-semibold">Rolling 7d Volatility ($)</th>
                        <th className="p-3 font-semibold">DoW Sin / Cos</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/50">
                      {featureData.timeseries_summary.sample_records.map((rec, i) => (
                        <tr key={i} className="hover:bg-secondary/20 transition-colors">
                          <td className="p-3 font-mono font-medium text-foreground">{rec.date}</td>
                          <td className="p-3 font-mono text-emerald-400">${rec.daily_revenue}</td>
                          <td className="p-3 text-foreground">{rec.daily_orders}</td>
                          <td className="p-3 font-mono text-muted-foreground">${rec.revenue_lag_1}</td>
                          <td className="p-3 font-mono text-muted-foreground">${rec.revenue_lag_7}</td>
                          <td className="p-3 font-mono text-primary font-medium">${rec.revenue_rolling_mean_7}</td>
                          <td className="p-3 font-mono text-amber-400">±${rec.revenue_rolling_std_7}</td>
                          <td className="p-3 font-mono text-muted-foreground">
                            {rec.day_of_week_sin} / {rec.day_of_week_cos}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      ) : (
        <Card className="border-border bg-card p-8 text-center">
          <div className="max-w-md mx-auto space-y-3">
            <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <Layers className="h-6 w-6" />
            </div>
            <h3 className="text-base font-semibold text-foreground">Compute Model-Ready Feature Store</h3>
            <p className="text-xs text-muted-foreground">
              Extract RFM vectors, customer purchase inter-arrival intervals, regularized daily sales series, rolling momentum averages, and cyclical date features.
            </p>
            <Button
              size="sm"
              onClick={handleGenerateFeatures}
              disabled={generating}
              className="mt-2 text-xs flex items-center gap-2 mx-auto bg-primary text-primary-foreground"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${generating ? 'animate-spin' : ''}`} />
              {generating ? 'Extracting Feature Store...' : 'Extract Engineered Features'}
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
