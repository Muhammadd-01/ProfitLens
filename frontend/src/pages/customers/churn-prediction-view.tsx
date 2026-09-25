import { useState, useEffect } from 'react';
import {
  AlertTriangle,
  Sparkles,
  TrendingDown,
  Award,
  RefreshCw,
  Info,
  ChevronDown,
  ChevronUp,
  Search,
  Filter,
  DollarSign,
  ShieldAlert,
  ArrowRight,
  HelpCircle,
  FileCode,
  Activity,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Target,
  ExternalLink,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';
import type {
  ChurnOverviewResponse,
  CustomerChurnRisk,
  ChurnCustomerListResponse,
  Dataset,
} from '@/types';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from 'recharts';

interface ChurnPredictionViewProps {
  dataset: Dataset;
}

export function ChurnPredictionView({ dataset }: ChurnPredictionViewProps) {
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);
  const [overview, setOverview] = useState<ChurnOverviewResponse | null>(null);
  const [customers, setCustomers] = useState<CustomerChurnRisk[]>([]);
  const [totalCustomers, setTotalCustomers] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>('auto');
  const [selectedInactivity, setSelectedInactivity] = useState<string>('auto');
  const [showPedagogy, setShowPedagogy] = useState(false);

  useEffect(() => {
    if (dataset?.id) {
      loadOverviewAndCustomers(dataset.id);
    }
  }, [dataset?.id]);

  useEffect(() => {
    if (dataset?.id && overview) {
      loadCustomers(dataset.id, page, riskFilter, searchQuery);
    }
  }, [page, riskFilter]);

  const loadOverviewAndCustomers = async (datasetId: string) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get<ChurnOverviewResponse>(`/ml/${datasetId}/churn/overview`);
      setOverview(resp.data);
      await loadCustomers(datasetId, 1, riskFilter, searchQuery);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Unable to load churn prediction. Please verify customer and transaction mappings.';
      setError(msg);
      setOverview(null);
    } finally {
      setLoading(false);
    }
  };

  const loadCustomers = async (
    datasetId: string,
    p: number,
    filter: string,
    search: string
  ) => {
    try {
      const params: Record<string, any> = { page: p, page_size: pageSize };
      if (filter && filter !== 'all') params.risk_level = filter;
      if (search) params.search = search;

      const resp = await api.get<ChurnCustomerListResponse>(
        `/ml/${datasetId}/churn/customers`,
        { params }
      );
      setCustomers(resp.data.customers);
      setTotalCustomers(resp.data.total);
    } catch {
      // Handled silently
    }
  };

  const handleRetrain = async () => {
    if (!dataset) return;
    setTraining(true);
    setError(null);
    try {
      const payload: Record<string, any> = { model_type: selectedModel };
      if (selectedInactivity !== 'auto') {
        payload.inactivity_threshold_days = Number(selectedInactivity);
      }
      const resp = await api.post<ChurnOverviewResponse>(
        `/ml/${dataset.id}/churn/train`,
        payload
      );
      setOverview(resp.data);
      setPage(1);
      await loadCustomers(dataset.id, 1, riskFilter, searchQuery);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Churn retraining failed.';
      setError(msg);
    } finally {
      setTraining(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadCustomers(dataset.id, 1, riskFilter, searchQuery);
  };

  const getRocAucGrade = (score: number) => {
    if (score >= 0.85) return { label: 'Excellent Discrimination', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' };
    if (score >= 0.70) return { label: 'Good Discrimination', color: 'text-blue-400 bg-blue-500/10 border-blue-500/30' };
    if (score >= 0.60) return { label: 'Fair Predictive Power', color: 'text-amber-400 bg-amber-500/10 border-amber-500/30' };
    return { label: 'Weak Discrimination', color: 'text-rose-400 bg-rose-500/10 border-rose-500/30' };
  };

  const getRiskBadge = (level: string, score: number) => {
    const pct = (score * 100).toFixed(0);
    switch (level.toLowerCase()) {
      case 'critical':
        return (
          <Badge className="bg-rose-500/15 text-rose-400 border-rose-500/30 hover:bg-rose-500/25">
            Critical ({pct}%)
          </Badge>
        );
      case 'high':
        return (
          <Badge className="bg-orange-500/15 text-orange-400 border-orange-500/30 hover:bg-orange-500/25">
            High ({pct}%)
          </Badge>
        );
      case 'medium':
        return (
          <Badge className="bg-amber-500/15 text-amber-400 border-amber-500/30 hover:bg-amber-500/25">
            Medium ({pct}%)
          </Badge>
        );
      default:
        return (
          <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/25">
            Low ({pct}%)
          </Badge>
        );
    }
  };

  const totalPages = Math.ceil(totalCustomers / pageSize) || 1;

  return (
    <div className="space-y-6">
      {/* Hyperparameter Tuning & Retrain Control Bar */}
      <Card className="bg-card border-border">
        <CardContent className="py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-semibold text-foreground">Supervised Churn Model Tuning</p>
              <p className="text-[11px] text-muted-foreground">
                Compare ensemble decision trees against regularized logistic regression with observation split.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-muted-foreground font-medium">Model:</span>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="bg-background border border-border rounded-md px-2.5 py-1 text-xs text-foreground font-medium"
                disabled={training || loading}
              >
                <option value="auto">Auto-Select (Champion AUC)</option>
                <option value="random_forest">Random Forest Classifier</option>
                <option value="logistic_regression">Logistic Regression (L2)</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-xs text-muted-foreground font-medium">Inactivity:</span>
              <select
                value={selectedInactivity}
                onChange={(e) => setSelectedInactivity(e.target.value)}
                className="bg-background border border-border rounded-md px-2.5 py-1 text-xs text-foreground font-medium"
                disabled={training || loading}
              >
                <option value="auto">Auto-Adaptive Window</option>
                <option value="30">30 Days Inactive</option>
                <option value="60">60 Days Inactive</option>
                <option value="90">90 Days Inactive</option>
              </select>
            </div>

            <Button
              size="sm"
              onClick={handleRetrain}
              disabled={training || loading}
              className="text-xs gap-1.5 font-medium"
            >
              <Sparkles className={`h-3.5 w-3.5 ${training ? 'animate-spin' : ''}`} />
              {training ? 'Training...' : 'Retrain Churn Model'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Error Banner */}
      {error && (
        <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 p-4 text-xs text-rose-400 flex items-start gap-3">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold">Unable to run churn prediction</p>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && !overview && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="animate-pulse bg-card border-border p-4 h-24" />
            ))}
          </div>
          <Card className="animate-pulse bg-card border-border p-6 h-72" />
        </div>
      )}

      {/* Main Churn Overview when loaded */}
      {overview && (
        <>
          {/* Top KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="bg-card border-border border-l-4 border-l-rose-500">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Total Revenue at Risk
                </CardTitle>
                <div className="rounded-lg bg-rose-500/10 p-2 text-rose-400">
                  <DollarSign className="h-4 w-4" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tracking-tight text-foreground">
                  ${overview.total_revenue_at_risk.toLocaleString()}
                </div>
                <p className="mt-1 text-xs text-rose-400/90 font-medium">
                  From High & Critical accounts
                </p>
              </CardContent>
            </Card>

            <Card className="bg-card border-border border-l-4 border-l-orange-500">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Critical Attrition Cohort
                </CardTitle>
                <div className="rounded-lg bg-orange-500/10 p-2 text-orange-400">
                  <TrendingDown className="h-4 w-4" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tracking-tight text-foreground">
                  {overview.risk_distribution.critical_count.toLocaleString()}{' '}
                  <span className="text-xs font-normal text-muted-foreground">
                    ({overview.risk_distribution.critical_pct}%)
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  P(churn) ≥ 75% dormancy probability
                </p>
              </CardContent>
            </Card>

            <Card className="bg-card border-border border-l-4 border-l-primary">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Model ROC-AUC Score
                </CardTitle>
                <div className="rounded-lg bg-primary/10 p-2 text-primary">
                  <Award className="h-4 w-4" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tracking-tight text-foreground">
                  {overview.metrics.roc_auc.toFixed(3)}
                </div>
                <div className="mt-1 flex items-center gap-1.5">
                  <Badge
                    variant="outline"
                    className={`text-[10px] px-1.5 py-0 ${getRocAucGrade(overview.metrics.roc_auc).color}`}
                  >
                    {getRocAucGrade(overview.metrics.roc_auc).label}
                  </Badge>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card border-border border-l-4 border-l-blue-500">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Champion Architecture
                </CardTitle>
                <div className="rounded-lg bg-blue-500/10 p-2 text-blue-400">
                  <Activity className="h-4 w-4" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-sm font-bold tracking-tight text-foreground truncate">
                  {overview.model_type_used}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Acc: {(overview.metrics.accuracy * 100).toFixed(1)}% • F1: {overview.metrics.f1_score.toFixed(2)}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Pedagogical Collapsible Accordion */}
          <Card className="bg-card/70 border-border/70 overflow-hidden">
            <div
              onClick={() => setShowPedagogy(!showPedagogy)}
              className="px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-muted/30 transition-colors"
            >
              <div className="flex items-center gap-2.5">
                <div className="p-1.5 rounded-md bg-rose-500/10 text-rose-400">
                  <Info className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-xs font-semibold text-foreground tracking-tight flex items-center gap-2">
                    Data Science Deep-Dive: Supervised Churn Modeling, Observation Windows, and Retention ROI
                  </h3>
                  <p className="text-[11px] text-muted-foreground">
                    Learn how ProfitLens formulates non-leaking outcome windows, mitigates class imbalance, and ranks risk drivers.
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
                      <Target className="h-3.5 w-3.5 text-rose-400" /> 1. The Non-Contractual Churn Challenge
                    </p>
                    <p>
                      In non-contractual commerce, customers never announce their departure; they simply stop purchasing. Defining churn requires setting an inactivity horizon window.
                    </p>
                    <p>
                      <strong>Leakage Prevention:</strong> If a model simply trains on current recency to predict current churn, it creates a trivial identity mapping. Instead, ProfitLens splits transactions into an Observation Window [T_min, T_cutoff] and an Outcome Window [T_cutoff, T_max]. Features are calculated strictly from the observation window, and target label y is evaluated on outcome return.
                    </p>
                  </div>

                  <div className="space-y-1.5 p-3 rounded-lg bg-muted/20 border border-border/40">
                    <p className="font-semibold text-foreground flex items-center gap-1.5">
                      <FileCode className="h-3.5 w-3.5 text-blue-400" /> 2. Class Imbalance & Cost Sensitivity
                    </p>
                    <p>
                      In healthy retail, active buyers outnumber churners (e.g. 80/20 split). Naive classifiers optimize overall accuracy by predicting "retained" for everyone.
                    </p>
                    <p>
                      ProfitLens enforces inverse-frequency loss weighting:
                      w_j = N / (2 * N_j). This penalizes False Negatives (missing a churning high-value customer) proportionally more than False Positives.
                    </p>
                  </div>

                  <div className="space-y-1.5 p-3 rounded-lg bg-muted/20 border border-border/40">
                    <p className="font-semibold text-foreground flex items-center gap-1.5">
                      <Activity className="h-3.5 w-3.5 text-emerald-400" /> 3. ROC-AUC & Precision-Recall Trade-off
                    </p>
                    <p>
                      <strong>ROC-AUC:</strong> Measures ranking discrimination across all classification thresholds: the probability that a randomly drawn churner is ranked higher than a non-churner.
                    </p>
                    <p>
                      <strong>Threshold Economics:</strong> Rather than forcing a static 0.5 decision cutoff, ProfitLens outputs continuous probabilities P(churn) stratified into 4 operational action tiers.
                    </p>
                  </div>

                  <div className="space-y-1.5 p-3 rounded-lg bg-muted/20 border border-border/40">
                    <p className="font-semibold text-foreground flex items-center gap-1.5">
                      <Award className="h-3.5 w-3.5 text-purple-400" /> 4. Gini Impurity Feature Importances
                    </p>
                    <p>
                      Ensemble trees measure Mean Decrease in Impurity (MDI). Features that consistently create pure splits across 100 bootstrapped trees are awarded higher importance scores, explaining the primary drivers behind business churn.
                    </p>
                  </div>
                </div>
              </CardContent>
            )}
          </Card>

          {/* Model Evaluation & Feature Drivers Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Risk Tier Population Breakdown */}
            <Card className="bg-card border-border">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-bold text-foreground">
                  Churn Risk Tier Distribution
                </CardTitle>
                <CardDescription className="text-xs">
                  Stratified customer counts across probability tiers
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Horizontal progress bar strip */}
                <div className="h-4 w-full rounded-full overflow-hidden flex bg-muted/40 border border-border/60">
                  <div
                    style={{ width: `${overview.risk_distribution.critical_pct}%` }}
                    className="bg-rose-500 transition-all"
                    title={`Critical: ${overview.risk_distribution.critical_pct}%`}
                  />
                  <div
                    style={{ width: `${overview.risk_distribution.high_pct}%` }}
                    className="bg-orange-500 transition-all"
                    title={`High: ${overview.risk_distribution.high_pct}%`}
                  />
                  <div
                    style={{ width: `${overview.risk_distribution.medium_pct}%` }}
                    className="bg-amber-500 transition-all"
                    title={`Medium: ${overview.risk_distribution.medium_pct}%`}
                  />
                  <div
                    style={{ width: `${overview.risk_distribution.low_pct}%` }}
                    className="bg-emerald-500 transition-all"
                    title={`Low: ${overview.risk_distribution.low_pct}%`}
                  />
                </div>

                {/* 4-tier cards */}
                <div className="grid grid-cols-2 gap-3 pt-2">
                  <div className="p-3 rounded-lg border border-rose-500/30 bg-rose-500/5 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-rose-400">Critical Risk</span>
                      <span className="text-[10px] text-muted-foreground font-mono">P ≥ 75%</span>
                    </div>
                    <p className="text-lg font-bold text-foreground">
                      {overview.risk_distribution.critical_count.toLocaleString()}{' '}
                      <span className="text-xs font-normal text-muted-foreground">
                        ({overview.risk_distribution.critical_pct}%)
                      </span>
                    </p>
                    <p className="text-[11px] text-muted-foreground">Immediate rescue needed</p>
                  </div>

                  <div className="p-3 rounded-lg border border-orange-500/30 bg-orange-500/5 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-orange-400">High Risk</span>
                      <span className="text-[10px] text-muted-foreground font-mono">50% ≤ P &lt; 75%</span>
                    </div>
                    <p className="text-lg font-bold text-foreground">
                      {overview.risk_distribution.high_count.toLocaleString()}{' '}
                      <span className="text-xs font-normal text-muted-foreground">
                        ({overview.risk_distribution.high_pct}%)
                      </span>
                    </p>
                    <p className="text-[11px] text-muted-foreground">Targeted re-activation</p>
                  </div>

                  <div className="p-3 rounded-lg border border-amber-500/30 bg-amber-500/5 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-amber-400">Medium Risk</span>
                      <span className="text-[10px] text-muted-foreground font-mono">25% ≤ P &lt; 50%</span>
                    </div>
                    <p className="text-lg font-bold text-foreground">
                      {overview.risk_distribution.medium_count.toLocaleString()}{' '}
                      <span className="text-xs font-normal text-muted-foreground">
                        ({overview.risk_distribution.medium_pct}%)
                      </span>
                    </p>
                    <p className="text-[11px] text-muted-foreground">Engagement check-in</p>
                  </div>

                  <div className="p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/5 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-emerald-400">Low Risk</span>
                      <span className="text-[10px] text-muted-foreground font-mono">P &lt; 25%</span>
                    </div>
                    <p className="text-lg font-bold text-foreground">
                      {overview.risk_distribution.low_count.toLocaleString()}{' '}
                      <span className="text-xs font-normal text-muted-foreground">
                        ({overview.risk_distribution.low_pct}%)
                      </span>
                    </p>
                    <p className="text-[11px] text-muted-foreground">Healthy, repeat buyer</p>
                  </div>
                </div>

                {/* Confusion Matrix Diagnostic */}
                <div className="pt-2 border-t border-border/50">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-foreground">
                      Validation Confusion Matrix (Test Set)
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      Precision: {(overview.metrics.precision * 100).toFixed(0)}% • Recall:{' '}
                      {(overview.metrics.recall * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-center text-xs">
                    <div className="p-2 rounded bg-muted/30 border border-border/40">
                      <p className="text-[10px] text-muted-foreground uppercase">True Negative (Retained)</p>
                      <p className="text-sm font-bold text-emerald-400 mt-0.5">
                        {overview.metrics.confusion_matrix.tn}
                      </p>
                    </div>
                    <div className="p-2 rounded bg-muted/30 border border-border/40">
                      <p className="text-[10px] text-muted-foreground uppercase">False Positive (False Alarm)</p>
                      <p className="text-sm font-bold text-amber-400 mt-0.5">
                        {overview.metrics.confusion_matrix.fp}
                      </p>
                    </div>
                    <div className="p-2 rounded bg-muted/30 border border-border/40">
                      <p className="text-[10px] text-muted-foreground uppercase">False Negative (Missed Churn)</p>
                      <p className="text-sm font-bold text-rose-400 mt-0.5">
                        {overview.metrics.confusion_matrix.fn}
                      </p>
                    </div>
                    <div className="p-2 rounded bg-muted/30 border border-border/40">
                      <p className="text-[10px] text-muted-foreground uppercase">True Positive (Caught Churn)</p>
                      <p className="text-sm font-bold text-blue-400 mt-0.5">
                        {overview.metrics.confusion_matrix.tp}
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Feature Importance Drivers */}
            <Card className="bg-card border-border flex flex-col justify-between">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-bold text-foreground">
                  Top Churn Risk Drivers (Feature Importance)
                </CardTitle>
                <CardDescription className="text-xs">
                  Normalized algorithmic weights indicating which behavioral patterns drive attrition
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-2">
                <div className="h-[320px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={overview.top_features}
                      layout="vertical"
                      margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#262626" horizontal={false} />
                      <XAxis
                        type="number"
                        stroke="#737373"
                        fontSize={10}
                        tickLine={false}
                        domain={[0, 'dataMax + 0.05']}
                        tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                      />
                      <YAxis
                        type="category"
                        dataKey="feature_name"
                        stroke="#737373"
                        fontSize={10}
                        tickLine={false}
                        width={130}
                        tickFormatter={(v) => v.replace(/_/g, ' ')}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#171717',
                          borderColor: '#333',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                        formatter={(val: any) => [`${(Number(val) * 100).toFixed(1)}%`, 'Relative Weight']}
                      />
                      <Bar dataKey="importance_score" fill="#6366f1" radius={[0, 4, 4, 0]}>
                        {overview.top_features.map((_, idx) => (
                          <Cell
                            key={`cell-${idx}`}
                            fill={idx === 0 ? '#ef4444' : idx < 3 ? '#f97316' : '#6366f1'}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Individual Customers Table & Filters */}
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <CardTitle className="text-sm font-bold text-foreground">
                    At-Risk Customers & Recommended Retention Playbooks
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Individual customer risk scoring with automated intervention recommendations
                  </CardDescription>
                </div>

                {/* Filters */}
                <div className="flex flex-wrap items-center gap-2">
                  {/* Search */}
                  <form onSubmit={handleSearchSubmit} className="relative">
                    <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                    <Input
                      type="text"
                      placeholder="Search Customer ID..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-8 h-8 text-xs w-44 bg-background"
                    />
                  </form>

                  {/* Filter Pills */}
                  <div className="flex items-center gap-1 bg-muted/40 p-0.5 rounded-lg border border-border">
                    {['all', 'critical', 'high', 'medium', 'low'].map((tier) => (
                      <button
                        key={tier}
                        onClick={() => {
                          setRiskFilter(tier);
                          setPage(1);
                        }}
                        className={`px-2.5 py-1 text-xs rounded-md font-medium capitalize transition-colors ${
                          riskFilter === tier
                            ? 'bg-background text-foreground shadow-sm'
                            : 'text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        {tier}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </CardHeader>

            <CardContent className="pt-0">
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-muted/40 text-muted-foreground uppercase text-[10px] tracking-wider border-b border-border">
                    <tr>
                      <th className="px-4 py-3">Customer ID</th>
                      <th className="px-4 py-3">Risk Tier</th>
                      <th className="px-4 py-3 text-right">Spend</th>
                      <th className="px-4 py-3 text-right">Orders</th>
                      <th className="px-4 py-3 text-right">Recency</th>
                      <th className="px-4 py-3">Top Risk Contributing Factors</th>
                      <th className="px-4 py-3">Retention Playbook Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {customers.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="text-center py-8 text-muted-foreground">
                          No customer records match the selected filters.
                        </td>
                      </tr>
                    ) : (
                      customers.map((cust) => (
                        <tr key={cust.customer_id} className="hover:bg-muted/20 transition-colors">
                          <td className="px-4 py-3 font-mono font-medium text-foreground">
                            {cust.customer_id}
                          </td>
                          <td className="px-4 py-3">
                            {getRiskBadge(cust.churn_risk_level, cust.churn_risk_score)}
                          </td>
                          <td className="px-4 py-3 text-right font-semibold text-foreground">
                            ${cust.monetary_total.toLocaleString()}
                          </td>
                          <td className="px-4 py-3 text-right text-foreground">
                            {cust.frequency}x
                          </td>
                          <td className="px-4 py-3 text-right text-foreground">
                            {cust.recency_days}d
                          </td>
                          <td className="px-4 py-3 max-w-xs">
                            <div className="flex flex-wrap gap-1">
                              {cust.top_risk_factors.map((factor, i) => (
                                <span
                                  key={i}
                                  className="inline-block px-1.5 py-0.5 rounded bg-muted text-[10px] text-muted-foreground leading-tight"
                                >
                                  {factor}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-foreground/90 max-w-sm">
                            <span className="line-clamp-2 leading-relaxed">
                              {cust.recommended_action}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between pt-4 border-t border-border mt-4 text-xs text-muted-foreground">
                <span>
                  Showing {customers.length} of {totalCustomers.toLocaleString()} customers
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                    disabled={page <= 1}
                    className="h-7 px-2 text-xs"
                  >
                    <ChevronLeft className="h-3.5 w-3.5 mr-1" /> Prev
                  </Button>
                  <span className="text-xs font-medium text-foreground">
                    Page {page} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                    disabled={page >= totalPages}
                    className="h-7 px-2 text-xs"
                  >
                    Next <ChevronRight className="h-3.5 w-3.5 ml-1" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
