import { useState, useEffect } from 'react';
import {
  AlertTriangle,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  RefreshCw,
  Search,
  Filter,
  DollarSign,
  TrendingUp,
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  Eye,
  ChevronDown,
  ChevronUp,
  Info,
  Sliders,
  Database,
  HelpCircle,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/common/empty-state';
import { useDatasetStore } from '@/stores/dataset-store';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import type {
  AnomalyItem,
  AnomalyOverviewResponse,
  Dataset,
} from '@/types';
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from 'recharts';

export function AnomaliesPage() {
  const { datasets, activeDataset, setActiveDataset, setDatasets } = useDatasetStore();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [overview, setOverview] = useState<AnomalyOverviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Filters & Controls
  const [sensitivity, setSensitivity] = useState<'conservative' | 'balanced' | 'aggressive'>('balanced');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showPedagogy, setShowPedagogy] = useState(false);
  const [selectedAnomaly, setSelectedAnomaly] = useState<AnomalyItem | null>(null);

  useEffect(() => {
    if (datasets.length === 0) {
      loadDatasets();
    } else if (activeDataset?.id) {
      loadAnomalies(activeDataset.id);
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
        loadAnomalies(first.id);
      } else {
        setLoading(false);
      }
    } catch {
      setLoading(false);
    }
  };

  const loadAnomalies = async (datasetId: string) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get<AnomalyOverviewResponse>(`/ml/${datasetId}/anomalies/list`);
      setOverview(resp.data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Unable to load anomaly scan results. Please ensure orders and revenue columns are mapped.';
      setError(msg);
      setOverview(null);
    } finally {
      setLoading(false);
    }
  };

  const handleRunDetection = async () => {
    if (!activeDataset) return;
    setScanning(true);
    setError(null);
    try {
      const contaminationMap = {
        conservative: 0.01,
        balanced: 0.02,
        aggressive: 0.05,
      };
      const resp = await api.post<AnomalyOverviewResponse>(
        `/ml/${activeDataset.id}/anomalies/detect`,
        {
          sensitivity,
          contamination: contaminationMap[sensitivity],
        }
      );
      setOverview(resp.data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Anomaly detection scan failed.';
      setError(msg);
    } finally {
      setScanning(false);
    }
  };

  const handleReviewAnomaly = async (
    anomalyId: string,
    newStatus: 'confirmed_fraud' | 'operational_glitch' | 'false_positive'
  ) => {
    if (!activeDataset) return;
    setReviewingId(anomalyId);
    try {
      const resp = await api.patch<AnomalyItem>(
        `/ml/${activeDataset.id}/anomalies/${anomalyId}/review`,
        {
          review_status: newStatus,
          notes: `Reviewed by operator as ${newStatus.replace('_', ' ')}`,
        }
      );
      // Update local state smoothly
      if (overview) {
        const updatedList = overview.anomalies.map((item) =>
          item.id === anomalyId ? resp.data : item
        );
        const reviewedCount = updatedList.filter((a) => a.is_reviewed).length;
        setOverview({
          ...overview,
          distribution: {
            ...overview.distribution,
            reviewed_count: reviewedCount,
          },
          anomalies: updatedList,
        });
        if (selectedAnomaly?.id === anomalyId) {
          setSelectedAnomaly(resp.data);
        }
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Review update failed.';
      setError(msg);
    } finally {
      setReviewingId(null);
    }
  };

  // Filter anomalies list
  const filteredAnomalies = (overview?.anomalies || []).filter((item) => {
    if (severityFilter !== 'all' && item.severity !== severityFilter) return false;
    if (statusFilter === 'pending' && item.is_reviewed) return false;
    if (statusFilter === 'reviewed' && !item.is_reviewed) return false;
    if (statusFilter === 'confirmed_fraud' && item.review_status !== 'confirmed_fraud') return false;
    if (statusFilter === 'operational_glitch' && item.review_status !== 'operational_glitch') return false;
    if (statusFilter === 'false_positive' && item.review_status !== 'false_positive') return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchOrd = item.order_id.toLowerCase().includes(q);
      const matchCust = item.customer_id?.toLowerCase().includes(q) || false;
      const matchReason = item.reason.toLowerCase().includes(q);
      return matchOrd || matchCust || matchReason;
    }
    return true;
  });

  const getSeverityBadgeClass = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/10 text-red-600 border-red-500/20';
      case 'high':
        return 'bg-amber-500/10 text-amber-600 border-amber-500/20';
      case 'medium':
        return 'bg-blue-500/10 text-blue-600 border-blue-500/20';
      default:
        return 'bg-slate-500/10 text-slate-600 border-slate-500/20';
    }
  };

  const getStatusBadge = (status: string, isReviewed: boolean) => {
    if (!isReviewed || status === 'pending') {
      return (
        <Badge variant="outline" className="border-amber-500/40 text-amber-600 bg-amber-500/10">
          <Clock className="w-3 h-3 mr-1" />
          Pending Review
        </Badge>
      );
    }
    if (status === 'confirmed_fraud') {
      return (
        <Badge variant="outline" className="border-red-500/40 text-red-600 bg-red-500/10">
          <ShieldAlert className="w-3 h-3 mr-1" />
          Confirmed Fraud
        </Badge>
      );
    }
    if (status === 'operational_glitch') {
      return (
        <Badge variant="outline" className="border-purple-500/40 text-purple-600 bg-purple-500/10">
          <AlertTriangle className="w-3 h-3 mr-1" />
          System Glitch
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="border-emerald-500/40 text-emerald-600 bg-emerald-500/10">
        <CheckCircle2 className="w-3 h-3 mr-1" />
        False Positive
      </Badge>
    );
  };

  // Prepare scatter chart data
  const scatterData = (overview?.anomalies || []).map((item, idx) => ({
    x: idx + 1,
    y: item.amount,
    z: item.anomaly_score,
    orderId: item.order_id,
    date: item.order_date,
    reason: item.reason,
    severity: item.severity,
    customer: item.customer_id || 'Unknown',
  }));

  const getSeverityColor = (sev: string) => {
    if (sev === 'critical') return '#ef4444';
    if (sev === 'high') return '#f59e0b';
    if (sev === 'medium') return '#3b82f6';
    return '#64748b';
  };

  if (datasets.length === 0 && !loading) {
    return (
      <div className="p-8">
        <EmptyState
          icon={ShieldAlert}
          title="No Datasets Uploaded"
          description="Upload an e-commerce or ERP transaction dataset to run isolation forest anomaly detection."
          actionLabel="Upload Dataset"
          onAction={() => navigate('/dashboard/datasets')}
        />
      </div>
    );
  }

  return (
    <div className="space-y-8 p-6 max-w-7xl mx-auto">
      {/* Top Banner / Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-red-500/10 text-red-600">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Transaction Anomaly Detection</h1>
              <p className="text-sm text-muted-foreground">
                Unsupervised Isolation Forest & Modified Z-Score engine for fraudulent transactions and revenue leakage.
              </p>
            </div>
          </div>
        </div>

        {/* Dataset & Action Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 bg-muted/60 px-3 py-1.5 rounded-lg border text-sm">
            <Database className="w-4 h-4 text-muted-foreground" />
            <select
              className="bg-transparent font-medium focus:outline-none cursor-pointer text-xs sm:text-sm"
              value={activeDataset?.id || ''}
              onChange={(e) => {
                const ds = datasets.find((d) => d.id === e.target.value);
                if (ds) {
                  setActiveDataset(ds);
                  loadAnomalies(ds.id);
                }
              }}
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 bg-muted/60 px-3 py-1.5 rounded-lg border text-sm">
            <Sliders className="w-4 h-4 text-muted-foreground" />
            <select
              className="bg-transparent font-medium focus:outline-none cursor-pointer text-xs sm:text-sm"
              value={sensitivity}
              onChange={(e) => setSensitivity(e.target.value as any)}
            >
              <option value="conservative">Conservative (1% Contam)</option>
              <option value="balanced">Balanced (2% Contam)</option>
              <option value="aggressive">Aggressive (5% Contam)</option>
            </select>
          </div>

          <Button
            onClick={handleRunDetection}
            disabled={scanning || loading || !activeDataset}
            className="gap-2 bg-red-600 hover:bg-red-700 text-white shadow-sm"
          >
            <RefreshCw className={`w-4 h-4 ${scanning ? 'animate-spin' : ''}`} />
            {scanning ? 'Scanning...' : 'Scan Anomalies'}
          </Button>

          <Button
            variant="outline"
            onClick={() => setShowPedagogy(!showPedagogy)}
            className="gap-2 text-xs"
          >
            <HelpCircle className="w-4 h-4 text-blue-500" />
            Algorithm Deep Dive
            {showPedagogy ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </Button>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            <p className="text-sm font-medium">{error}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={() => setError(null)}>
            Dismiss
          </Button>
        </div>
      )}

      {/* Section 38 Pedagogical Deep-Dive Accordion */}
      {showPedagogy && (
        <Card className="border-blue-500/30 bg-blue-500/5 transition-all">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2 text-blue-600 font-semibold text-lg">
              <Sparkles className="w-5 h-5" />
              Educational Masterclass: Isolation Forest & Modified Z-Score (MAD)
            </div>
            <CardDescription className="text-xs sm:text-sm">
              Comprehensive mathematical breakdown of unsupervised anomaly detection in commercial transaction streams.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5 text-sm">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-lg bg-card border space-y-2">
                <h4 className="font-semibold text-foreground flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-500" />
                  1. The Business Problem
                </h4>
                <p className="text-muted-foreground text-xs leading-relaxed">
                  Commercial ledgers suffer from checkout exploits, rogue promotional discounts, unauthorized employee
                  rebates, data entry typos ($10,000 instead of $100.00), and card-testing velocity attacks. Left unflagged,
                  revenue leaks permanently and corrupts financial forecasting.
                </p>
              </div>

              <div className="p-4 rounded-lg bg-card border space-y-2">
                <h4 className="font-semibold text-foreground flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-500" />
                  2. The Data Science Problem
                </h4>
                <p className="text-muted-foreground text-xs leading-relaxed">
                  Real transaction databases have <strong>no ground-truth fraud labels</strong>. Supervised models fail due
                  to zero positive labels. We formulate this as an <em>unsupervised multi-dimensional anomaly detection</em>
                  problem: outliers are "few and different", isolating rapidly in tree partitions.
                </p>
              </div>
            </div>

            {/* Math Foundations */}
            <div className="p-4 rounded-lg bg-card border space-y-3">
              <h4 className="font-semibold text-foreground flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-indigo-500" />
                3. Mathematical Foundations
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="space-y-2 bg-muted/40 p-3 rounded-md">
                  <p className="font-mono font-semibold text-primary">Isolation Tree (iTree) Path Length:</p>
                  <p className="text-muted-foreground">
                    Anomalies require significantly fewer random splits to isolate than normal cluster instances:
                  </p>
                  <div className="font-mono bg-background p-2 rounded border text-center text-xs">
                    s(x, n) = 2^{`{-\\frac{E(h(x))}{c(n)}}`}
                  </div>
                  <p className="text-muted-foreground">
                    Where <code className="font-mono font-bold">c(n) = 2 ln(n-1) + 0.5772 - 2(n-1)/n</code> is Euler's harmonic number average path length of an unsuccessful search in a Binary Search Tree (BST). When <code className="font-mono text-primary">s &gt; 0.6</code>, the point is strongly anomalous.
                  </p>
                </div>

                <div className="space-y-2 bg-muted/40 p-3 rounded-md">
                  <p className="font-mono font-semibold text-primary">Modified Z-Score (Boris Iglewicz & David Hoaglin):</p>
                  <p className="text-muted-foreground">
                    Standard Z-Score <code className="font-mono font-bold">(x - μ)/σ</code> fails on skewed financial distributions because extreme values inflate the sample mean and variance (the <em>masking effect</em>).
                  </p>
                  <div className="font-mono bg-background p-2 rounded border text-center text-xs">
                    M_i = 0.6745 · (x_i - Median(X)) / MAD
                  </div>
                  <p className="text-muted-foreground">
                    Where <code className="font-mono font-bold">MAD = Median(|X - Median(X)|)</code>. The factor <code className="font-mono">0.6745</code> scales the MAD to estimate standard deviation under normal distributions. Points with <code className="font-mono text-primary">|M_i| &gt; 3.5</code> are robust statistical anomalies.
                  </p>
                </div>
              </div>
            </div>

            {/* Explanation & Rules */}
            <div className="p-4 rounded-lg bg-card border space-y-2">
              <h4 className="font-semibold text-foreground flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                4. Operational Review Loop
              </h4>
              <p className="text-muted-foreground text-xs leading-relaxed">
                ProfitLens fuses Isolation Forest multivariate depth with Category-Relative Median ratios and customer velocity.
                Each flagged order generates a deterministic explanation badge and enters a human-in-the-loop review queue
                enabling operators to triage whether an outlier was a genuine high-value customer order, an accidental duplicate,
                or active payment fraud.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center space-y-4">
          <RefreshCw className="w-8 h-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Scanning transactions and computing Isolation Forest tree paths...</p>
        </div>
      ) : overview ? (
        <>
          {/* Executive KPI Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="border-red-500/20 bg-gradient-to-br from-red-500/5 via-card to-card">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground">Flagged Exposure</span>
                  <div className="p-2 rounded-lg bg-red-500/10 text-red-600">
                    <DollarSign className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-2xl font-bold tracking-tight text-red-600">
                    ${overview.distribution.total_flagged_revenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Cumulative monetary risk across {overview.distribution.total_anomalies} flagged transactions
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-amber-500/20 bg-gradient-to-br from-amber-500/5 via-card to-card">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground">Total Anomalies</span>
                  <div className="p-2 rounded-lg bg-amber-500/10 text-amber-600">
                    <AlertTriangle className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-2xl font-bold tracking-tight">
                    {overview.distribution.total_anomalies}{' '}
                    <span className="text-xs font-normal text-muted-foreground">
                      / {overview.total_orders_scanned} scanned
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 mt-2">
                    <Badge variant="outline" className="text-[10px] bg-red-500/10 text-red-600 border-red-500/20">
                      {overview.distribution.critical_count} Critical
                    </Badge>
                    <Badge variant="outline" className="text-[10px] bg-amber-500/10 text-amber-600 border-amber-500/20">
                      {overview.distribution.high_count} High
                    </Badge>
                    <Badge variant="outline" className="text-[10px] bg-blue-500/10 text-blue-600 border-blue-500/20">
                      {overview.distribution.medium_count} Med
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground">Critical Tiers</span>
                  <div className="p-2 rounded-lg bg-red-500/10 text-red-600">
                    <ShieldAlert className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-2xl font-bold tracking-tight text-red-600">
                    {overview.distribution.critical_count}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Orders with Isolation Score &ge; 0.65 or Modified Z-Score &ge; 5.0
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground">Investigation Status</span>
                  <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-600">
                    <ShieldCheck className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-2xl font-bold tracking-tight text-emerald-600">
                    {overview.distribution.reviewed_count}{' '}
                    <span className="text-xs font-normal text-muted-foreground">
                      / {overview.distribution.total_anomalies} reviewed
                    </span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-1.5 mt-2 overflow-hidden">
                    <div
                      className="bg-emerald-500 h-1.5 rounded-full transition-all duration-500"
                      style={{
                        width: `${
                          overview.distribution.total_anomalies > 0
                            ? (overview.distribution.reviewed_count / overview.distribution.total_anomalies) * 100
                            : 0
                        }%`,
                      }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Interactive Scatter Chart: Outlier Monetary Magnitude vs Order Sequence */}
          <Card className="border-border">
            <CardHeader className="pb-2">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <CardTitle className="text-base font-semibold flex items-center gap-2">
                    <Activity className="w-4 h-4 text-primary" />
                    Anomaly Isolation Landscape
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Multi-dimensional outlier plot. Node size and color represent Isolation Forest anomaly score magnitude.
                  </CardDescription>
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-red-500" /> Critical
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> High
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-blue-500" /> Medium
                  </span>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-[280px] w-full pt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                    <XAxis
                      type="number"
                      dataKey="x"
                      name="Anomaly Sequence"
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      domain={[0, 'dataMax + 1']}
                    />
                    <YAxis
                      type="number"
                      dataKey="y"
                      name="Amount ($)"
                      tickFormatter={(val) => `$${val >= 1000 ? `${(val / 1000).toFixed(1)}k` : val}`}
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                    />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div className="p-3 bg-card border rounded-lg shadow-xl text-xs space-y-1">
                              <p className="font-semibold text-foreground">{data.orderId}</p>
                              <p className="text-muted-foreground">Customer: {data.customer}</p>
                              <p className="text-muted-foreground">Date: {data.date}</p>
                              <p className="font-medium text-foreground">Amount: ${data.y.toFixed(2)}</p>
                              <p className="font-mono text-primary">Score: {(data.z * 100).toFixed(1)}%</p>
                              <p className="text-[11px] text-amber-500 italic max-w-xs">{data.reason}</p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Scatter name="Anomalies" data={scatterData}>
                      {scatterData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={getSeverityColor(entry.severity)}
                          opacity={0.85}
                          r={Math.max(5, entry.z * 10)}
                        />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Anomaly Investigation Table & Drawer */}
          <Card className="border-border">
            <CardHeader className="pb-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <CardTitle className="text-base font-semibold flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-red-500" />
                    Flagged Transactions Queue
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Operator triage queue with algorithmic explanations, category medians, and resolution actions.
                  </CardDescription>
                </div>

                {/* Filter and Search Bar */}
                <div className="flex flex-wrap items-center gap-2.5">
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted-foreground" />
                    <input
                      type="text"
                      placeholder="Search order, customer, reason..."
                      className="pl-8 pr-3 py-1.5 text-xs bg-muted/50 border rounded-lg focus:outline-none focus:ring-1 focus:ring-primary w-52"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>

                  <select
                    className="text-xs bg-muted/50 border rounded-lg px-2.5 py-1.5 focus:outline-none cursor-pointer"
                    value={severityFilter}
                    onChange={(e) => setSeverityFilter(e.target.value)}
                  >
                    <option value="all">All Severities</option>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>

                  <select
                    className="text-xs bg-muted/50 border rounded-lg px-2.5 py-1.5 focus:outline-none cursor-pointer"
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                  >
                    <option value="all">All Statuses</option>
                    <option value="pending">Pending Review</option>
                    <option value="reviewed">Reviewed</option>
                    <option value="confirmed_fraud">Confirmed Fraud</option>
                    <option value="operational_glitch">System Glitch</option>
                    <option value="false_positive">False Positive</option>
                  </select>
                </div>
              </div>
            </CardHeader>

            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-muted/50 border-y text-muted-foreground uppercase tracking-wider text-[10px]">
                    <tr>
                      <th className="py-3 px-4">Order ID & Date</th>
                      <th className="py-3 px-4">Customer</th>
                      <th className="py-3 px-4">Amount</th>
                      <th className="py-3 px-4">Anomaly Score</th>
                      <th className="py-3 px-4">Severity</th>
                      <th className="py-3 px-4">Algorithmic Explanation</th>
                      <th className="py-3 px-4">Review Status</th>
                      <th className="py-3 px-4 text-right">Triage Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {filteredAnomalies.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="text-center py-8 text-muted-foreground">
                          No transactions match the selected filters.
                        </td>
                      </tr>
                    ) : (
                      filteredAnomalies.map((item) => (
                        <tr key={item.id} className="hover:bg-muted/30 transition-colors">
                          <td className="py-3 px-4">
                            <div className="font-semibold text-foreground">{item.order_id}</div>
                            <div className="text-[11px] text-muted-foreground">{item.order_date}</div>
                          </td>
                          <td className="py-3 px-4 text-muted-foreground font-mono">
                            {item.customer_id || 'N/A'}
                          </td>
                          <td className="py-3 px-4 font-semibold text-foreground">
                            ${item.amount.toFixed(2)}
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-1.5">
                              <span className="font-mono font-medium text-foreground">
                                {(item.anomaly_score * 100).toFixed(1)}%
                              </span>
                              <div className="w-12 bg-muted rounded-full h-1.5 overflow-hidden">
                                <div
                                  className="h-full rounded-full"
                                  style={{
                                    width: `${Math.min(100, item.anomaly_score * 100)}%`,
                                    backgroundColor: getSeverityColor(item.severity),
                                  }}
                                />
                              </div>
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <Badge variant="outline" className={`capitalize text-[10px] ${getSeverityBadgeClass(item.severity)}`}>
                              {item.severity}
                            </Badge>
                          </td>
                          <td className="py-3 px-4 max-w-xs">
                            <span className="text-xs text-foreground line-clamp-2" title={item.reason}>
                              {item.reason}
                            </span>
                            {item.details?.category_ratio && item.details.category_ratio > 1 && (
                              <span className="text-[10px] text-muted-foreground block mt-0.5">
                                {item.details.category_ratio}x category median (${item.details.category_median?.toFixed(2) || '0'})
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4">
                            {getStatusBadge(item.review_status, item.is_reviewed)}
                          </td>
                          <td className="py-3 px-4 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 px-2 text-[11px] text-red-600 hover:bg-red-500/10 hover:text-red-700"
                                disabled={reviewingId === item.id}
                                onClick={() => handleReviewAnomaly(item.id, 'confirmed_fraud')}
                                title="Confirm Fraud"
                              >
                                Fraud
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 px-2 text-[11px] text-purple-600 hover:bg-purple-500/10 hover:text-purple-700"
                                disabled={reviewingId === item.id}
                                onClick={() => handleReviewAnomaly(item.id, 'operational_glitch')}
                                title="System Glitch"
                              >
                                Glitch
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 px-2 text-[11px] text-emerald-600 hover:bg-emerald-500/10 hover:text-emerald-700"
                                disabled={reviewingId === item.id}
                                onClick={() => handleReviewAnomaly(item.id, 'false_positive')}
                                title="False Positive"
                              >
                                Valid
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
