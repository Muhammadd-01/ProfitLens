import { useState, useEffect } from 'react';
import {
  Lightbulb,
  Sparkles,
  RefreshCw,
  Search,
  Filter,
  AlertTriangle,
  AlertOctagon,
  CheckCircle2,
  Info,
  TrendingUp,
  Users,
  Package,
  ShieldAlert,
  MessageSquareQuote,
  DollarSign,
  ChevronDown,
  ChevronUp,
  Eye,
  EyeOff,
  Database,
  ArrowRight,
  BookOpen,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/common/empty-state';
import { useDatasetStore } from '@/stores/dataset-store';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import type {
  InsightItem,
  InsightFeedResponse,
  Dataset,
} from '@/types';

export function InsightsPage() {
  const { datasets, activeDataset, setActiveDataset, setDatasets } = useDatasetStore();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [feed, setFeed] = useState<InsightFeedResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [showDismissed, setShowDismissed] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showPedagogy, setShowPedagogy] = useState<boolean>(false);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  useEffect(() => {
    if (datasets.length === 0) {
      loadDatasets();
    } else if (activeDataset?.id) {
      loadInsights(activeDataset.id);
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
        loadInsights(first.id);
      } else {
        setLoading(false);
      }
    } catch {
      setLoading(false);
    }
  };

  const loadInsights = async (datasetId: string) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get<InsightFeedResponse>(`/insights/${datasetId}/feed`);
      setFeed(resp.data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Unable to load executive insights. Ensure your dataset has valid transactions or sales.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!activeDataset?.id) return;
    setGenerating(true);
    setError(null);
    try {
      const resp = await api.post<InsightFeedResponse>(`/insights/${activeDataset.id}/generate`);
      setFeed(resp.data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Insights generation failed.';
      setError(msg);
    } finally {
      setGenerating(false);
    }
  };

  const handleDismissToggle = async (insight: InsightItem) => {
    if (!activeDataset?.id) return;
    const newDismissedState = !insight.is_dismissed;
    setActionInProgress(insight.id);
    try {
      await api.patch(`/insights/${activeDataset.id}/${insight.id}/dismiss`, {
        dismissed: newDismissedState,
      });

      // Update state locally
      if (feed) {
        const updatedInsights = feed.insights.map((item) =>
          item.id === insight.id ? { ...item, is_dismissed: newDismissedState } : item
        );

        // Recompute summary
        const activeItems = updatedInsights.filter((i) => !i.is_dismissed);
        const newSummary = {
          critical_count: activeItems.filter((i) => i.severity === 'critical').length,
          warning_count: activeItems.filter((i) => i.severity === 'warning').length,
          positive_count: activeItems.filter((i) => i.severity === 'positive').length,
          info_count: activeItems.filter((i) => i.severity === 'info').length,
          total_insights: activeItems.length,
        };

        setFeed({
          ...feed,
          summary: newSummary,
          insights: updatedInsights,
        });
      }
    } catch (err: unknown) {
      console.error('Failed to toggle insight dismissal', err);
    } finally {
      setActionInProgress(null);
    }
  };

  // Filter insights
  const filteredInsights = (feed?.insights || []).filter((item) => {
    // Dismissal status
    if (showDismissed) {
      if (!item.is_dismissed) return false;
    } else {
      if (item.is_dismissed) return false;
    }

    // Category
    if (selectedCategory !== 'all' && item.category !== selectedCategory) {
      return false;
    }

    // Severity
    if (selectedSeverity !== 'all' && item.severity !== selectedSeverity) {
      return false;
    }

    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = item.title.toLowerCase().includes(q);
      const matchDesc = item.description.toLowerCase().includes(q);
      const matchAction = item.recommended_action.toLowerCase().includes(q);
      if (!matchTitle && !matchDesc && !matchAction) return false;
    }

    return true;
  });

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'critical':
        return (
          <Badge className="bg-red-500/10 text-red-500 border-red-500/30 flex items-center gap-1">
            <AlertOctagon className="w-3.5 h-3.5" /> Critical
          </Badge>
        );
      case 'warning':
        return (
          <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/30 flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5" /> Warning
          </Badge>
        );
      case 'positive':
        return (
          <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/30 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" /> Positive
          </Badge>
        );
      case 'info':
      default:
        return (
          <Badge className="bg-blue-500/10 text-blue-500 border-blue-500/30 flex items-center gap-1">
            <Info className="w-3.5 h-3.5" /> Info
          </Badge>
        );
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'revenue':
        return <DollarSign className="w-4 h-4 text-emerald-500" />;
      case 'churn':
      case 'customers':
        return <Users className="w-4 h-4 text-purple-500" />;
      case 'products':
        return <Package className="w-4 h-4 text-blue-500" />;
      case 'anomalies':
        return <ShieldAlert className="w-4 h-4 text-red-500" />;
      case 'sentiment':
        return <MessageSquareQuote className="w-4 h-4 text-pink-500" />;
      case 'forecast':
        return <TrendingUp className="w-4 h-4 text-indigo-500" />;
      default:
        return <Sparkles className="w-4 h-4 text-amber-500" />;
    }
  };

  const categories = [
    { id: 'all', label: 'All Modules' },
    { id: 'revenue', label: 'Revenue Momentum' },
    { id: 'churn', label: 'Customer Churn' },
    { id: 'products', label: 'Product Catalog' },
    { id: 'anomalies', label: 'Anomalies & Fraud' },
    { id: 'sentiment', label: 'Customer Sentiment' },
  ];

  if (!activeDataset && !loading) {
    return (
      <EmptyState
        icon={Database}
        title="No Datasets Available"
        description="Upload or connect a transaction dataset to generate automated executive business insights."
        actionLabel="Go to Datasets"
        onAction={() => navigate('/dashboard/datasets')}
      />
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header & Dataset Selection */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <Lightbulb className="w-6 h-6 text-amber-500" />
              Automated Executive Insights Engine
            </h1>
            <Badge variant="outline" className="text-xs font-mono">
              Phase 16 Active
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Deterministic rule-based heuristics synthesizing revenue momentum, churn risk, product BCG matrices, anomaly triage, and customer sentiment into prioritized prescriptive actions.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Dataset Switcher */}
          <div className="flex items-center gap-2 bg-card border rounded-lg px-3 py-1.5 shadow-xs">
            <Database className="w-4 h-4 text-muted-foreground" />
            <select
              className="bg-transparent text-sm font-medium focus:outline-none"
              value={activeDataset?.id || ''}
              onChange={(e) => {
                const found = datasets.find((d) => d.id === e.target.value);
                if (found) {
                  setActiveDataset(found);
                  loadInsights(found.id);
                }
              }}
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id} className="bg-card text-foreground">
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          <Button
            onClick={handleGenerate}
            disabled={generating || loading}
            className="flex items-center gap-2"
          >
            {generating ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4 text-amber-300" />
            )}
            {generating ? 'Synthesizing...' : 'Re-evaluate Insights'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-500 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <Button variant="ghost" size="sm" onClick={() => loadInsights(activeDataset!.id)}>
            Retry
          </Button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="border-border/50 bg-gradient-to-br from-card to-card/60">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Active Insights
              </span>
              <Lightbulb className="w-4 h-4 text-muted-foreground" />
            </div>
            <div className="text-2xl font-bold mt-2 text-foreground">
              {feed?.summary.total_insights ?? 0}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Ranked by impact & confidence
            </div>
          </CardContent>
        </Card>

        <Card className="border-red-500/20 bg-red-500/5">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-red-500 uppercase tracking-wider">
                Critical Severity
              </span>
              <AlertOctagon className="w-4 h-4 text-red-500" />
            </div>
            <div className="text-2xl font-bold mt-2 text-red-500">
              {feed?.summary.critical_count ?? 0}
            </div>
            <div className="text-xs text-red-500/80 mt-1">
              Requires immediate C-suite intervention
            </div>
          </CardContent>
        </Card>

        <Card className="border-amber-500/20 bg-amber-500/5">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-amber-500 uppercase tracking-wider">
                Warnings & Risks
              </span>
              <AlertTriangle className="w-4 h-4 text-amber-500" />
            </div>
            <div className="text-2xl font-bold mt-2 text-amber-500">
              {feed?.summary.warning_count ?? 0}
            </div>
            <div className="text-xs text-amber-500/80 mt-1">
              Elevated churn or operational friction
            </div>
          </CardContent>
        </Card>

        <Card className="border-emerald-500/20 bg-emerald-500/5">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-emerald-500 uppercase tracking-wider">
                Growth & Milestones
              </span>
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            </div>
            <div className="text-2xl font-bold mt-2 text-emerald-500">
              {feed?.summary.positive_count ?? 0}
            </div>
            <div className="text-xs text-emerald-500/80 mt-1">
              Expansion opportunities & top traction
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Control Bar & Category Filters */}
      <div className="space-y-3">
        {/* Category Tabs */}
        <div className="flex flex-wrap items-center gap-2 border-b pb-3">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                selectedCategory === cat.id
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'bg-card hover:bg-muted text-muted-foreground border'
              }`}
            >
              {cat.label}
            </button>
          ))}

          <div className="ml-auto flex items-center gap-2">
            <Button
              variant={showDismissed ? 'secondary' : 'outline'}
              size="sm"
              onClick={() => setShowDismissed(!showDismissed)}
              className="text-xs flex items-center gap-1.5"
            >
              {showDismissed ? (
                <>
                  <Eye className="w-3.5 h-3.5 text-primary" /> Showing Dismissed
                </>
              ) : (
                <>
                  <EyeOff className="w-3.5 h-3.5 text-muted-foreground" /> View Dismissed
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Severity Filter & Search Bar */}
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search insights by title, description, or action..."
              className="w-full pl-9 pr-4 py-2 bg-card border rounded-lg text-sm placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Filter className="w-4 h-4 text-muted-foreground shrink-0" />
            <select
              className="bg-card border rounded-lg px-3 py-2 text-sm focus:outline-none w-full sm:w-auto"
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="warning">Warning</option>
              <option value="positive">Positive</option>
              <option value="info">Info</option>
            </select>
          </div>
        </div>
      </div>

      {/* Insight Stream */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <RefreshCw className="w-8 h-8 animate-spin text-primary mb-3" />
          <p className="text-sm text-muted-foreground">Evaluating cross-module heuristic decision rules...</p>
        </div>
      ) : filteredInsights.length === 0 ? (
        <div className="p-12 text-center border rounded-xl bg-card">
          <Lightbulb className="w-12 h-12 text-muted-foreground mx-auto mb-3 opacity-40" />
          <h3 className="text-base font-medium text-foreground">No Insights Found</h3>
          <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
            {showDismissed
              ? 'No dismissed insights matching the current filters.'
              : 'All business metrics are either within normal bounds or no active insights match your current filters.'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredInsights.map((insight) => {
            const isCritical = insight.severity === 'critical';
            const isWarning = insight.severity === 'warning';
            const isPositive = insight.severity === 'positive';

            return (
              <Card
                key={insight.id}
                className={`transition-all duration-200 border ${
                  isCritical
                    ? 'border-red-500/40 bg-gradient-to-r from-red-500/[0.04] to-transparent shadow-xs'
                    : isWarning
                    ? 'border-amber-500/40 bg-gradient-to-r from-amber-500/[0.03] to-transparent'
                    : isPositive
                    ? 'border-emerald-500/40 bg-gradient-to-r from-emerald-500/[0.03] to-transparent'
                    : 'border-border/60 hover:border-border'
                }`}
              >
                <CardContent className="p-5">
                  <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                    {/* Main Content */}
                    <div className="space-y-2 flex-1">
                      {/* Top Badges */}
                      <div className="flex flex-wrap items-center gap-2">
                        {getSeverityBadge(insight.severity)}
                        <Badge variant="outline" className="flex items-center gap-1 text-xs">
                          {getCategoryIcon(insight.category)}
                          <span className="capitalize">{insight.category}</span>
                        </Badge>
                        <Badge variant="secondary" className="text-xs font-mono">
                          {Math.round(insight.confidence * 100)}% Confidence
                        </Badge>
                        <span className="text-xs text-muted-foreground ml-auto md:ml-0">
                          Impact Score: {insight.impact_score.toFixed(1)}
                        </span>
                      </div>

                      {/* Title & Description */}
                      <div>
                        <h3 className="text-base font-semibold text-foreground tracking-tight">
                          {insight.title}
                        </h3>
                        <p className="text-sm text-muted-foreground mt-1 leading-relaxed">
                          {insight.description}
                        </p>
                      </div>

                      {/* Metrics Pills */}
                      {insight.metrics && Object.keys(insight.metrics).length > 0 && (
                        <div className="flex flex-wrap items-center gap-2 pt-1">
                          {Object.entries(insight.metrics).map(([k, v]) => (
                            <span
                              key={k}
                              className="inline-flex items-center text-xs font-mono bg-muted/60 border px-2.5 py-0.5 rounded-md text-foreground"
                            >
                              <span className="text-muted-foreground mr-1.5 capitalize">
                                {k.replace(/_/g, ' ')}:
                              </span>
                              <strong>
                                {typeof v === 'number'
                                  ? Math.abs(v) > 1000
                                    ? `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
                                    : typeof v === 'number' && !Number.isInteger(v)
                                    ? v.toFixed(2)
                                    : v
                                  : String(v)}
                              </strong>
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Recommended Prescriptive Action Box */}
                      <div className="mt-3 p-3.5 rounded-lg bg-card/80 border border-primary/20 shadow-2xs space-y-1.5">
                        <div className="flex items-center gap-1.5 text-xs font-semibold text-primary uppercase tracking-wide">
                          <ArrowRight className="w-3.5 h-3.5" /> Prescriptive Operational Playbook
                        </div>
                        <p className="text-xs text-foreground/90 font-medium leading-normal">
                          {insight.recommended_action}
                        </p>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex md:flex-col items-center justify-end gap-2 shrink-0 pt-2 md:pt-0">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={actionInProgress === insight.id}
                        onClick={() => handleDismissToggle(insight)}
                        className="text-xs w-full justify-center"
                      >
                        {insight.is_dismissed ? (
                          <>
                            <Eye className="w-3.5 h-3.5 mr-1 text-emerald-500" /> Restore
                          </>
                        ) : (
                          <>
                            <EyeOff className="w-3.5 h-3.5 mr-1 text-muted-foreground" /> Dismiss
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Section 38 Pedagogical Masterclass Accordion */}
      <Card className="border-border/60 bg-muted/20 mt-8">
        <CardHeader
          className="cursor-pointer py-4"
          onClick={() => setShowPedagogy(!showPedagogy)}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-primary" />
              <CardTitle className="text-base font-semibold">
                Section 38 Masterclass: Automated Executive Insights & Prescriptive Analytics Engine
              </CardTitle>
            </div>
            {showPedagogy ? (
              <ChevronUp className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            )}
          </div>
          <CardDescription className="text-xs">
            Architectural principles of converting multi-domain ML outputs into prioritized executive decision workflows.
          </CardDescription>
        </CardHeader>

        {showPedagogy && (
          <CardContent className="space-y-6 pt-0 text-sm text-foreground/90 leading-relaxed border-t border-border/40">
            {/* 1. Business Problem */}
            <div className="space-y-1.5 pt-4">
              <h4 className="font-bold text-primary flex items-center gap-2 text-sm">
                1. Business Problem
              </h4>
              <p>
                Executives and merchants suffer from "dashboard fatigue" and cognitive overload. While modern SaaS platforms produce dozens of disparate charts (churn ROC curves, ARIMA sales forecasts, Isolation Forest anomaly lists, BCG product scatter plots, and ABSA sentiment breakdowns), busy leaders rarely have the bandwidth to synthesize these signals manually. Without unified triage, critical operational emergencies (e.g. $10,000+ of imminent customer churn or rapid rating deterioration in a flagship product) remain buried until financial losses have already occurred.
              </p>
            </div>

            {/* 2. Data Science Problem */}
            <div className="space-y-1.5">
              <h4 className="font-bold text-primary flex items-center gap-2 text-sm">
                2. Data Science Problem
              </h4>
              <p>
                Transforming heterogeneous analytical signals into a unified, prioritized decision feed requires Multi-Criteria Decision Analysis (MCDA). We must formalize:
              </p>
              <ul className="list-disc pl-5 space-y-1 text-xs text-muted-foreground">
                <li>Cross-domain normalization of continuous loss values (dollars at risk vs. percentage contractions vs. review volume).</li>
                <li>Confidence weighting to discount noisy signals from small sample sizes.</li>
                <li>Severity tiering into deterministic buckets (Critical, Warning, Positive, Informational) with guaranteed idempotence.</li>
              </ul>
            </div>

            {/* 3. Relevant Concept */}
            <div className="space-y-1.5">
              <h4 className="font-bold text-primary flex items-center gap-2 text-sm">
                3. Relevant Concept: Prescriptive Analytics & Expert Rule Engines
              </h4>
              <p>
                Analytics maturity evolves across four stages: Descriptive (What happened?), Diagnostic (Why did it happen?), Predictive (What will happen?), and Prescriptive (What should we do?). The ProfitLens Executive Insights Engine represents Level 4 (Prescriptive Analytics). Rather than hallucinating open-ended text via large generative models that risk generating ungrounded financial advice, ProfitLens employs a deterministic expert rule engine paired with dynamic narrative synthesis templates and concrete merchant playbooks.
              </p>
            </div>

            {/* 4. Mathematics */}
            <div className="space-y-1.5">
              <h4 className="font-bold text-primary flex items-center gap-2 text-sm">
                4. Mathematical Foundation: Multi-Attribute Utility Function
              </h4>
              <p>
                Every detected business insight candidate {'$x_i$'} is scored using a multi-attribute utility function that balances financial impact, statistical confidence, and inherent domain urgency:
              </p>
              <div className="p-3 bg-card border rounded-md font-mono text-xs overflow-x-auto my-2 text-center">
                {'Score(x_i) = \\alpha \\cdot \\text{Urgency}(S_i) + \\beta \\cdot \\log_{10}(1 + \\text{Impact}(x_i)) + \\gamma \\cdot \\text{Confidence}(x_i)'}
              </div>
              <p className="text-xs text-muted-foreground">
                Where urgency weights are stratified as {'$S_{\\text{critical}} = 100$'}, {'$S_{\\text{warning}} = 50$'}, {'$S_{\\text{positive}} = 30$'}, and {'$S_{\\text{info}} = 10$'}. Financial impact is log-scaled to avoid dominating the feed while strictly prioritizing solvency threats.
              </p>
            </div>

            {/* 5. Algorithm */}
            <div className="space-y-1.5">
              <h4 className="font-bold text-primary flex items-center gap-2 text-sm">
                5. The Algorithm: Multi-Domain Synthesis Pipeline
              </h4>
              <ol className="list-decimal pl-5 space-y-1 text-xs text-muted-foreground">
                <li><strong>Harvester</strong>: Reads tabular transactions and inspects cached downstream artifacts (Customer Churn models, ARIMA forecasts, Isolation Forest anomaly lists, Product BCG matrices, TF-IDF sentiment).</li>
                <li><strong>Rule Evaluator</strong>: Applies domain heuristic conditions (e.g., revenue contraction &le; -10%, high churn risk &ge; 15% of customer base, unresolved critical anomalies &gt; 0, BCG cash cows with falling velocity).</li>
                <li><strong>Template Interpolator</strong>: Formats quantitative metrics into human-readable executive narratives with exact financial citations.</li>
                <li><strong>Playbook Assigner</strong>: Attaches concrete prescriptive operational steps (e.g. reactivation discounts, SKU phase-out, gateway inspection).</li>
                <li><strong>Priority Sorter</strong>: Orders insights descending by composite utility score and filters out operator-dismissed items.</li>
              </ol>
            </div>

            {/* 6. Code Architecture */}
            <div className="space-y-1.5">
              <h4 className="font-bold text-primary flex items-center gap-2 text-sm">
                6. Code Architecture
              </h4>
              <p className="text-xs text-muted-foreground">
                The backend service resides in <code>app/services/insights_service.py</code> with endpoints exposed at <code>/api/insights/{'{dataset_id}'}/feed</code> and <code>/generate</code>. Operator dismissals are persisted in dataset metadata, ensuring zero disruption to multi-tenant isolation.
              </p>
            </div>

            {/* 7. Output Interpretation */}
            <div className="space-y-1.5">
              <h4 className="font-bold text-primary flex items-center gap-2 text-sm">
                7. Output Interpretation
              </h4>
              <p className="text-xs text-muted-foreground">
                <strong>Critical (Red)</strong>: Immediate revenue leakage or systemic security/operational risk requiring same-day executive attention.<br />
                <strong>Warning (Amber)</strong>: Degrading trends or concentration vulnerabilities that threaten next-quarter performance.<br />
                <strong>Positive (Emerald)</strong>: High-performing channels, SKU stars, or sentiment surges to double-down on.<br />
                <strong>Info (Blue)</strong>: Baseline operational benchmarks and system readiness notices.
              </p>
            </div>

            {/* 8. Limitations & Future Work */}
            <div className="space-y-1.5">
              <h4 className="font-bold text-primary flex items-center gap-2 text-sm">
                8. Limitations
              </h4>
              <p className="text-xs text-muted-foreground">
                Rule-based prescriptive analytics rely on domain threshold heuristics that must be calibrated as a merchant scales. Additionally, correlation between detected anomalies or churn indicators does not strictly guarantee causal intervention efficacy without A/B testing counterfactuals.
              </p>
            </div>
          </CardContent>
        )}
      </Card>
    </div>
  );
}
