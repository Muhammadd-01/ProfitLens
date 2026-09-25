import { useState, useEffect } from 'react';
import {
  TrendingUp,
  Sparkles,
  Calendar,
  DollarSign,
  Award,
  RefreshCw,
  Info,
  ChevronDown,
  ChevronUp,
  Database,
  Layers,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  ShieldAlert,
  Target,
  Sliders,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/common/empty-state';
import { useDatasetStore } from '@/stores/dataset-store';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import type { ForecastResponse, ForecastDataPoint, Dataset } from '@/types';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine,
} from 'recharts';

export function ForecastPage() {
  const { datasets, activeDataset, setActiveDataset, setDatasets } = useDatasetStore();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [horizon, setHorizon] = useState<number>(30);
  const [modelType, setModelType] = useState<string>('auto');
  const [confidenceLevel, setConfidenceLevel] = useState<number>(0.95);
  const [showPedagogy, setShowPedagogy] = useState(false);

  useEffect(() => {
    if (datasets.length === 0) {
      loadDatasets();
    } else if (activeDataset?.id) {
      loadForecast(activeDataset.id, horizon, confidenceLevel);
    } else if (datasets.length > 0) {
      setActiveDataset(datasets[0]);
    }
  }, [datasets.length, activeDataset?.id]);

  const loadDatasets = async () => {
    try {
      const resp = await api.get<{ datasets: Dataset[]; total: number }>('/datasets');
      setDatasets(resp.data.datasets);
      if (resp.data.datasets.length > 0) {
        const first = resp.data.datasets[0];
        setActiveDataset(first);
        loadForecast(first.id, horizon, confidenceLevel);
      } else {
        setLoading(false);
      }
    } catch {
      setLoading(false);
    }
  };

  const loadForecast = async (datasetId: string, h: number, conf: number) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get<ForecastResponse>(`/ml/${datasetId}/forecast/results`, {
        params: { horizon_days: h, confidence_level: conf },
      });
      setForecastData(resp.data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Unable to load sales forecast. Please ensure date and revenue columns are mapped.';
      setError(msg);
      setForecastData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateForecast = async () => {
    if (!activeDataset) return;
    setTraining(true);
    setError(null);
    try {
      const resp = await api.post<ForecastResponse>(
        `/ml/${activeDataset.id}/forecast/train`,
        {
          model_type: modelType,
          horizon_days: horizon,
          confidence_level: confidenceLevel,
        }
      );
      setForecastData(resp.data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Forecast generation failed.';
      setError(msg);
    } finally {
      setTraining(false);
    }
  };

  if (!activeDataset && datasets.length === 0) {
    return (
      <EmptyState
        icon={Database}
        title="No datasets available for forecasting"
        description="Upload a transaction dataset with order dates and sales revenue to generate statistical forward projections and confidence intervals."
        actionLabel="Go to Datasets"
        onAction={() => navigate('/dashboard/datasets')}
      />
    );
  }

  // Find boundary date between historical actuals and forward projections
  const cutoffPoint = forecastData?.series.find((p) => p.is_forecast);
  const cutoffDate = cutoffPoint ? cutoffPoint.date : undefined;

  const CustomForecastTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const point: ForecastDataPoint = payload[0]?.payload;
      return (
        <div className="bg-[#171717] border border-border/80 rounded-lg p-3 shadow-xl text-xs space-y-1.5 min-w-[210px]">
          <div className="flex items-center justify-between border-b border-border/50 pb-1.5">
            <span className="font-semibold text-foreground font-mono">{label}</span>
            <Badge
              variant="outline"
              className={`text-[10px] px-1.5 py-0 border-current ${
                point.is_forecast ? 'text-primary' : 'text-emerald-400'
              }`}
            >
              {point.is_forecast ? 'Forecast' : 'Historical'}
            </Badge>
          </div>
          <div className="space-y-1 pt-1">
            {!point.is_forecast && point.actual !== null && (
              <div className="flex justify-between text-muted-foreground">
                <span>Actual Revenue:</span>
                <span className="font-semibold text-emerald-400">${point.actual.toLocaleString()}</span>
              </div>
            )}
            <div className="flex justify-between text-muted-foreground">
              <span>{point.is_forecast ? 'Projected Revenue:' : 'Fitted Baseline:'}</span>
              <span className="font-semibold text-foreground">${point.predicted.toLocaleString()}</span>
            </div>
            {point.is_forecast && (
              <div className="flex justify-between text-[11px] text-muted-foreground border-t border-border/40 pt-1">
                <span>{(confidenceLevel * 100).toFixed(0)}% Range:</span>
                <span className="font-mono text-primary/90">
                  ${point.lower_bound.toLocaleString()} - ${point.upper_bound.toLocaleString()}
                </span>
              </div>
            )}
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Top Header & Dataset Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Sales Forecasting & Predictive Analytics
            </h1>
            <Badge variant="outline" className="text-xs bg-primary/10 text-primary border-primary/20">
              Time Series ML
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Holt-Winters Exponential Smoothing, ARIMA modeling, and statistical confidence intervals
          </p>
        </div>

        {/* Dataset Switcher & Controls */}
        <div className="flex items-center gap-3">
          {datasets.length > 1 && (
            <select
              value={activeDataset?.id || ''}
              onChange={(e) => {
                const found = datasets.find((d) => d.id === e.target.value);
                if (found) {
                  setActiveDataset(found);
                  loadForecast(found.id, horizon, confidenceLevel);
                }
              }}
              className="bg-card border border-border rounded-lg px-3 py-1.5 text-xs text-foreground font-medium"
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.row_count ? `${d.row_count.toLocaleString()} rows` : d.file_type})
                </option>
              ))}
            </select>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={() => activeDataset && loadForecast(activeDataset.id, horizon, confidenceLevel)}
            disabled={loading || training}
            className="text-xs gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading || training ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Model Controls & Scenario Configuration Bar */}
      <Card className="bg-card border-border">
        <CardContent className="py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Sliders className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-semibold text-foreground">Forecast Horizon & Scenario Controls</p>
              <p className="text-[11px] text-muted-foreground">
                Customize forward projection horizon, model algorithm, and prediction interval bounds.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-muted-foreground font-medium">Horizon:</span>
              <select
                value={horizon}
                onChange={(e) => setHorizon(Number(e.target.value))}
                className="bg-background border border-border rounded-md px-2.5 py-1 text-xs text-foreground font-medium"
                disabled={training || loading}
              >
                <option value={14}>14 Days (Short Term)</option>
                <option value={30}>30 Days (1 Month)</option>
                <option value={60}>60 Days (2 Months)</option>
                <option value={90}>90 Days (Quarterly)</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-xs text-muted-foreground font-medium">Model:</span>
              <select
                value={modelType}
                onChange={(e) => setModelType(e.target.value)}
                className="bg-background border border-border rounded-md px-2.5 py-1 text-xs text-foreground font-medium"
                disabled={training || loading}
              >
                <option value="auto">Auto-Select (Lowest RMSE)</option>
                <option value="holt_winters">Holt-Winters (ETS)</option>
                <option value="arima">ARIMA (1, 1, 1)</option>
                <option value="linear_trend">Linear Trend + Cyclical</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-xs text-muted-foreground font-medium">Confidence:</span>
              <select
                value={confidenceLevel}
                onChange={(e) => setConfidenceLevel(Number(e.target.value))}
                className="bg-background border border-border rounded-md px-2.5 py-1 text-xs text-foreground font-medium"
                disabled={training || loading}
              >
                <option value={0.95}>95% Interval (Standard)</option>
                <option value={0.80}>80% Interval (Narrow)</option>
              </select>
            </div>

            <Button
              size="sm"
              onClick={handleGenerateForecast}
              disabled={training || loading || !activeDataset}
              className="text-xs gap-1.5 font-medium"
            >
              <Sparkles className={`h-3.5 w-3.5 ${training ? 'animate-spin' : ''}`} />
              {training ? 'Computing...' : 'Project Sales'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Error Banner */}
      {error && (
        <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 p-4 text-xs text-rose-400 flex items-start gap-3">
          <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold">Forecast calculation issue</p>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && !forecastData && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="animate-pulse bg-card border-border p-4 h-24" />
            ))}
          </div>
          <Card className="animate-pulse bg-card border-border p-6 h-80" />
        </div>
      )}

      {/* Main Forecast Content when loaded */}
      {forecastData && (
        <>
          {/* Executive Metrics Overview */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="bg-card border-border border-l-4 border-l-primary">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Projected Revenue ({forecastData.horizon_days}d)
                </CardTitle>
                <div className="rounded-lg bg-primary/10 p-2 text-primary">
                  <DollarSign className="h-4 w-4" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tracking-tight text-foreground">
                  ${forecastData.projected_total_revenue.toLocaleString()}
                </div>
                {forecastData.projected_growth_pct !== null ? (
                  <div className="mt-1 flex items-center gap-1 text-xs">
                    {forecastData.projected_growth_pct >= 0 ? (
                      <span className="flex items-center text-emerald-400 font-medium">
                        <ArrowUpRight className="h-3.5 w-3.5 mr-0.5" />
                        +{forecastData.projected_growth_pct}%
                      </span>
                    ) : (
                      <span className="flex items-center text-rose-400 font-medium">
                        <ArrowDownRight className="h-3.5 w-3.5 mr-0.5" />
                        {forecastData.projected_growth_pct}%
                      </span>
                    )}
                    <span className="text-muted-foreground">vs prior period</span>
                  </div>
                ) : (
                  <p className="mt-1 text-xs text-muted-foreground">Future revenue estimate</p>
                )}
              </CardContent>
            </Card>

            <Card className="bg-card border-border border-l-4 border-l-emerald-500">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Out-of-Sample Accuracy
                </CardTitle>
                <div className="rounded-lg bg-emerald-500/10 p-2 text-emerald-400">
                  <Award className="h-4 w-4" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tracking-tight text-foreground">
                  {forecastData.metrics.mape !== null ? `${forecastData.metrics.mape}%` : 'N/A'}
                </div>
                <div className="mt-1 flex items-center gap-1.5">
                  <Badge variant="outline" className="text-[10px] px-1.5 py-0 text-emerald-400 border-emerald-500/30">
                    MAPE Error
                  </Badge>
                  <span className="text-[11px] text-muted-foreground font-mono">
                    RMSE: ${forecastData.metrics.rmse}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card border-border border-l-4 border-l-blue-500">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Trajectory & Trend
                </CardTitle>
                <div className="rounded-lg bg-blue-500/10 p-2 text-blue-400">
                  <TrendingUp className="h-4 w-4" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-xl font-bold tracking-tight text-foreground">
                  {forecastData.seasonality.trend_direction}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {forecastData.seasonality.growth_rate_pct > 0 ? '+' : ''}
                  {forecastData.seasonality.growth_rate_pct}% Annualized Momentum
                </p>
              </CardContent>
            </Card>

            <Card className="bg-card border-border border-l-4 border-l-purple-500">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Model Architecture
                </CardTitle>
                <div className="rounded-lg bg-purple-500/10 p-2 text-purple-400">
                  <Activity className="h-4 w-4" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-sm font-bold tracking-tight text-foreground truncate" title={forecastData.model_name}>
                  {forecastData.model_name}
                </div>
                <div className="mt-1 flex items-center gap-1.5">
                  <Badge variant="outline" className="text-[10px] px-1.5 py-0 text-purple-400 border-purple-500/30">
                    {(forecastData.confidence_level * 100).toFixed(0)}% Confidence
                  </Badge>
                  {forecastData.seasonality.seasonality_detected && (
                    <span className="text-[11px] text-muted-foreground">
                      Peak: {forecastData.seasonality.peak_day_of_week}
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Collapsible Pedagogical DS Module */}
          <Card className="bg-card/70 border-border/70 overflow-hidden">
            <div
              onClick={() => setShowPedagogy(!showPedagogy)}
              className="px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-muted/30 transition-colors"
            >
              <div className="flex items-center gap-2.5">
                <div className="p-1.5 rounded-md bg-blue-500/10 text-blue-400">
                  <Info className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-xs font-semibold text-foreground tracking-tight flex items-center gap-2">
                    Data Science Deep-Dive: Time-Series Regularization, Holt-Winters ETS, and Expanding Prediction Intervals
                  </h3>
                  <p className="text-[11px] text-muted-foreground">
                    Understand how ProfitLens handles calendar gaps, seasonal weekday patterns, and expanding uncertainty cones.
                  </p>
                </div>
              </div>
              <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-muted-foreground">
                {showPedagogy ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </div>

            {showPedagogy && (
              <CardContent className="pt-2 pb-6 px-6 border-t border-border/50 text-xs text-muted-foreground space-y-4 leading-relaxed">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1.5 p-3 rounded-lg bg-muted/20 border border-border/40">
                    <p className="font-semibold text-foreground flex items-center gap-1.5">
                      <Target className="h-3.5 w-3.5 text-primary" /> 1. Business & Data Science Problem
                    </p>
                    <p>
                      <strong>Business:</strong> Blind purchasing leads to either catastrophic inventory stockouts (lost revenue) or costly overstock storage fees. Financial leaders need probabilistic forward cash-flow horizons.
                    </p>
                    <p>
                      <strong>Data Science:</strong> Raw business data has episodic, irregular timestamps. We must resample data into a continuous daily grid, test for weekly cyclicality (period m=7), and decompose underlying momentum from noise.
                    </p>
                  </div>

                  <div className="space-y-1.5 p-3 rounded-lg bg-muted/20 border border-border/40">
                    <p className="font-semibold text-foreground flex items-center gap-1.5">
                      <Layers className="h-3.5 w-3.5 text-blue-400" /> 2. Holt-Winters Triple Smoothing (ETS)
                    </p>
                    <p>
                      Models three coupled state variables:
                    </p>
                    <ul className="list-disc pl-4 space-y-0.5">
                      <li>Level l_t = α(y_t - s_(t-m)) + (1 - α)(l_(t-1) + b_(t-1))</li>
                      <li>Trend b_t = β(l_t - l_(t-1)) + (1 - β)b_(t-1)</li>
                      <li>Season s_t = γ(y_t - l_(t-1) - b_(t-1)) + (1 - γ)s_(t-m)</li>
                    </ul>
                    <p>Forecast: ŷ_(t+h) = l_t + h·b_t + s_(t+h-m(k+1)).</p>
                  </div>

                  <div className="space-y-1.5 p-3 rounded-lg bg-muted/20 border border-border/40">
                    <p className="font-semibold text-foreground flex items-center gap-1.5">
                      <Activity className="h-3.5 w-3.5 text-emerald-400" /> 3. ARIMA(p, d, q) Modeling
                    </p>
                    <p>
                      Auto-Regressive Integrated Moving Average models stationarize non-stationary series via differencing (order d) and capture autoregressive dependencies (order p) and moving-average error shocks (order q).
                    </p>
                    <p>
                      Models are evaluated out-of-sample on a holdout test window before selecting the champion.
                    </p>
                  </div>

                  <div className="space-y-1.5 p-3 rounded-lg bg-muted/20 border border-border/40">
                    <p className="font-semibold text-foreground flex items-center gap-1.5">
                      <Award className="h-3.5 w-3.5 text-purple-400" /> 4. Expanding Confidence Intervals
                    </p>
                    <p>
                      Uncertainty naturally compounds as we peer further into the future. Forecast standard error expands with step h:
                      SE(h) = σ_ε · √(1 + c·h). For 95% confidence, bounds are ŷ_(t+h) ± 1.96·SE(h), clamped at zero to respect revenue non-negativity.
                    </p>
                  </div>
                </div>
              </CardContent>
            )}
          </Card>

          {/* Interactive Predictive Revenue Chart */}
          <Card className="bg-card border-border">
            <CardHeader className="pb-2">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <CardTitle className="text-sm font-semibold text-foreground">
                    Historical Sales Trajectory & Forward Forecast Horizon
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Continuous daily sales with model-projected mean and {(forecastData.confidence_level * 100).toFixed(0)}% confidence interval cone
                  </CardDescription>
                </div>
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-emerald-400" />
                    <span>Actual Sales</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-primary" />
                    <span>Forecast Mean</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="h-2.5 w-4 rounded bg-primary/20 border border-primary/40" />
                    <span>Confidence Cone</span>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-4">
              <div className="h-[400px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={forecastData.series} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                    <defs>
                      <linearGradient id="forecastBand" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--color-primary, #6366f1)" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="var(--color-primary, #6366f1)" stopOpacity={0.05} />
                      </linearGradient>
                      <linearGradient id="actualGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
                    <XAxis
                      dataKey="date"
                      stroke="#737373"
                      fontSize={10}
                      tickLine={false}
                      tickFormatter={(val) => {
                        if (val && val.length >= 10) return val.slice(5); // MM-DD
                        return val;
                      }}
                    />
                    <YAxis
                      stroke="#737373"
                      fontSize={10}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                    />
                    <Tooltip content={<CustomForecastTooltip />} />

                    {/* Boundary marker between history and future */}
                    {cutoffDate && (
                      <ReferenceLine
                        x={cutoffDate}
                        stroke="#a855f7"
                        strokeDasharray="4 4"
                        label={{
                          value: 'Forecast Cutoff',
                          position: 'top',
                          fill: '#a855f7',
                          fontSize: 10,
                        }}
                      />
                    )}

                    {/* Confidence upper bound area fill */}
                    <Area
                      type="monotone"
                      dataKey="upper_bound"
                      stroke="none"
                      fill="url(#forecastBand)"
                      fillOpacity={1}
                    />

                    {/* Historical Actual line */}
                    <Line
                      type="monotone"
                      dataKey="actual"
                      stroke="#10b981"
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4, fill: '#10b981' }}
                    />

                    {/* Predicted / Forecast line */}
                    <Line
                      type="monotone"
                      dataKey="predicted"
                      stroke="var(--color-primary, #6366f1)"
                      strokeWidth={2.5}
                      strokeDasharray="4 2"
                      dot={false}
                      activeDot={{ r: 5, fill: 'var(--color-primary, #6366f1)' }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Forecast Horizon Daily Data Table */}
          <Card className="bg-card border-border overflow-hidden">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-sm font-bold text-foreground">
                    Projected Daily Schedule & Confidence Bounds
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Next {forecastData.horizon_days} calendar days with bounded expectations
                  </CardDescription>
                </div>
                <Badge variant="outline" className="text-xs font-mono">
                  {forecastData.horizon_days} Days Forward
                </Badge>
              </div>
            </CardHeader>
            <div className="overflow-x-auto max-h-72">
              <table className="w-full text-xs text-left">
                <thead className="bg-muted/40 text-muted-foreground uppercase text-[10px] tracking-wider border-b border-border sticky top-0 bg-muted/90 backdrop-blur">
                  <tr>
                    <th className="px-4 py-2.5">Date</th>
                    <th className="px-4 py-2.5 text-right">Expected Revenue</th>
                    <th className="px-4 py-2.5 text-right">Lower Bound ({(confidenceLevel * 100).toFixed(0)}%)</th>
                    <th className="px-4 py-2.5 text-right">Upper Bound ({(confidenceLevel * 100).toFixed(0)}%)</th>
                    <th className="px-4 py-2.5 text-right">Uncertainty Spread</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {forecastData.series
                    .filter((p) => p.is_forecast)
                    .map((item) => {
                      const spread = item.upper_bound - item.lower_bound;
                      return (
                        <tr key={item.date} className="hover:bg-muted/20 transition-colors font-mono">
                          <td className="px-4 py-2 text-foreground font-medium font-sans">
                            {item.date}
                          </td>
                          <td className="px-4 py-2 text-right font-bold text-primary">
                            ${item.predicted.toLocaleString()}
                          </td>
                          <td className="px-4 py-2 text-right text-muted-foreground">
                            ${item.lower_bound.toLocaleString()}
                          </td>
                          <td className="px-4 py-2 text-right text-muted-foreground">
                            ${item.upper_bound.toLocaleString()}
                          </td>
                          <td className="px-4 py-2 text-right text-xs text-purple-400">
                            ±${(spread / 2.0).toFixed(0)}
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
