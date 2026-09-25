import { useState, useEffect } from 'react';
import {
  Users,
  Sparkles,
  Layers,
  Award,
  TrendingUp,
  RefreshCw,
  Info,
  ChevronDown,
  ChevronUp,
  Target,
  ShieldAlert,
  ArrowRight,
  Database,
  Compass,
  FileCode,
  Activity,
  CheckCircle2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/common/empty-state';
import { TableSkeleton } from '@/components/common/loading-skeleton';
import { useDatasetStore } from '@/stores/dataset-store';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import type { SegmentationTrainResponse, PCAPoint, Dataset } from '@/types';
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
  Legend,
} from 'recharts';
import { ChurnPredictionView } from './churn-prediction-view';

export function CustomerSegmentsPage() {
  const { datasets, activeDataset, setActiveDataset, setDatasets } = useDatasetStore();
  const navigate = useNavigate();

  const [mainModule, setMainModule] = useState<'segmentation' | 'churn'>('segmentation');
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);
  const [segmentData, setSegmentData] = useState<SegmentationTrainResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedK, setSelectedK] = useState<number | 'auto'>('auto');
  const [activeTab, setActiveTab] = useState<'pca' | 'diagnostics' | 'matrix'>('pca');
  const [showPedagogy, setShowPedagogy] = useState(false);

  // Initial load
  useEffect(() => {
    if (datasets.length === 0) {
      loadDatasets();
    } else if (activeDataset?.id) {
      loadSegmentation(activeDataset.id);
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
        loadSegmentation(first.id);
      } else {
        setLoading(false);
      }
    } catch {
      setLoading(false);
    }
  };

  const loadSegmentation = async (datasetId: string) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get<SegmentationTrainResponse>(`/ml/${datasetId}/segmentation/results`);
      setSegmentData(resp.data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Unable to load customer segmentation. Please ensure features have been engineered.';
      setError(msg);
      setSegmentData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleTrainClusters = async () => {
    if (!activeDataset) return;
    setTraining(true);
    setError(null);
    try {
      const payload = selectedK === 'auto' ? {} : { k: Number(selectedK) };
      const resp = await api.post<SegmentationTrainResponse>(
        `/ml/${activeDataset.id}/segmentation/train`,
        payload
      );
      setSegmentData(resp.data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Clustering run failed. Ensure your dataset has at least 5 customers.';
      setError(msg);
    } finally {
      setTraining(false);
    }
  };

  if (!activeDataset && datasets.length === 0) {
    return (
      <EmptyState
        icon={Database}
        title="No datasets available for segmentation"
        description="Upload a transactions dataset to unlock unsupervised customer clustering, behavioral personas, and targeted retention strategies."
        actionLabel="Go to Datasets"
        onAction={() => navigate('/dashboard/datasets')}
      />
    );
  }

  const getSilhouetteGrade = (score: number) => {
    if (score >= 0.5) return { label: 'Strong Structure', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' };
    if (score >= 0.35) return { label: 'Reasonable Structure', color: 'text-blue-400 bg-blue-500/10 border-blue-500/30' };
    if (score >= 0.2) return { label: 'Weak Structure', color: 'text-amber-400 bg-amber-500/10 border-amber-500/30' };
    return { label: 'Overlapping Clusters', color: 'text-rose-400 bg-rose-500/10 border-rose-500/30' };
  };

  const CustomScatterTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const point: PCAPoint = payload[0].payload;
      const seg = segmentData?.segments.find((s) => s.cluster_id === point.cluster_id);
      return (
        <div className="bg-[#171717] border border-border/80 rounded-lg p-3 shadow-xl text-xs space-y-1.5 min-w-[210px]">
          <div className="flex items-center justify-between border-b border-border/50 pb-1.5">
            <span className="font-semibold text-foreground font-mono">{point.customer_id}</span>
            <Badge
              variant="outline"
              className="text-[10px] px-1.5 py-0 border-current font-medium"
              style={{ color: seg?.color || '#3b82f6' }}
            >
              {point.label}
            </Badge>
          </div>
          <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-muted-foreground pt-1">
            <span>Lifetime Spend:</span>
            <span className="text-foreground font-medium text-right">${point.monetary.toLocaleString()}</span>
            <span>Total Orders:</span>
            <span className="text-foreground font-medium text-right">{point.frequency}</span>
            <span>Last Purchase:</span>
            <span className="text-foreground font-medium text-right">{point.recency}d ago</span>
            <span>PCA Coordinates:</span>
            <span className="text-muted-foreground font-mono text-[10px] text-right">({point.x}, {point.y})</span>
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
              {mainModule === 'segmentation' ? 'Customer Segmentation & K-Means' : 'Customer Churn Prediction & Retention'}
            </h1>
            <Badge
              variant="outline"
              className={`text-xs ${
                mainModule === 'segmentation'
                  ? 'bg-primary/10 text-primary border-primary/20'
                  : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
              }`}
            >
              {mainModule === 'segmentation' ? 'Unsupervised ML' : 'Supervised ML'}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            {mainModule === 'segmentation'
              ? 'Multi-dimensional behavioral clustering on RFM vectors with optimal k selection and 2D PCA projection'
              : 'Early attrition detection, observation window formulation, risk stratification, and automated playbooks'}
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
                  loadSegmentation(found.id);
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
            onClick={() => activeDataset && loadSegmentation(activeDataset.id)}
            disabled={loading || training}
            className="text-xs gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading || training ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Module Switcher Tabs */}
      <div className="flex items-center gap-2 border-b border-border pb-3">
        <button
          onClick={() => setMainModule('segmentation')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            mainModule === 'segmentation'
              ? 'bg-primary text-primary-foreground shadow-sm'
              : 'text-muted-foreground hover:bg-muted/40 hover:text-foreground'
          }`}
        >
          <Users className="h-4 w-4" />
          Behavioral Segmentation (K-Means & PCA)
        </button>
        <button
          onClick={() => setMainModule('churn')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            mainModule === 'churn'
              ? 'bg-rose-600 text-white shadow-sm'
              : 'text-muted-foreground hover:bg-muted/40 hover:text-foreground'
          }`}
        >
          <ShieldAlert className="h-4 w-4" />
          Customer Churn Prediction & Retention
        </button>
      </div>

      {mainModule === 'churn' && activeDataset ? (
        <ChurnPredictionView dataset={activeDataset} />
      ) : (
        <>
          {/* Cluster Fitting Controls Bar */}
      <Card className="bg-card border-border">
        <CardContent className="py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Compass className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-foreground">Cluster Hyperparameter Tuning</p>
              <p className="text-[11px] text-muted-foreground">
                Set cluster count $k$ manually or allow Silhouette optimization to discover natural boundaries.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground font-medium">Cluster Count $k$:</span>
              <select
                value={selectedK}
                onChange={(e) => setSelectedK(e.target.value === 'auto' ? 'auto' : Number(e.target.value))}
                className="bg-background border border-border rounded-md px-2.5 py-1 text-xs text-foreground font-medium"
                disabled={training || loading}
              >
                <option value="auto">Auto-Select (Optimal Silhouette)</option>
                <option value={2}>k = 2 (Broad Cohorts)</option>
                <option value={3}>k = 3 (Tiers: High, Med, Low)</option>
                <option value={4}>k = 4 (Recommended RFM Quads)</option>
                <option value={5}>k = 5 (Granular Personas)</option>
                <option value={6}>k = 6 (Micro-Segments)</option>
              </select>
            </div>

            <Button
              size="sm"
              onClick={handleTrainClusters}
              disabled={training || loading || !activeDataset}
              className="text-xs gap-1.5 font-medium"
            >
              <Sparkles className={`h-3.5 w-3.5 ${training ? 'animate-spin' : ''}`} />
              {training ? 'Fitting K-Means...' : 'Refit Clusters'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Error Banner */}
      {error && (
        <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 p-4 text-xs text-rose-400 flex items-start gap-3">
          <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold">Unable to cluster customers</p>
            <p>{error}</p>
            <Button
              variant="link"
              size="sm"
              onClick={() => navigate('/dashboard/datasets')}
              className="p-0 h-auto text-xs text-rose-300 underline font-normal"
            >
              Check feature engineering & column mappings in Datasets
            </Button>
          </div>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && !segmentData && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="animate-pulse bg-card border-border">
                <CardHeader className="pb-2">
                  <div className="h-4 bg-muted rounded w-24" />
                </CardHeader>
                <CardContent>
                  <div className="h-7 bg-muted rounded w-32 mb-2" />
                  <div className="h-3 bg-muted rounded w-20" />
                </CardContent>
              </Card>
            ))}
          </div>
          <Card className="animate-pulse bg-card border-border p-6 h-80" />
        </div>
      )}

      {/* Main Content when loaded */}
      {segmentData && (
        <>
          {/* Executive Metrics Overview */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="bg-card border-border">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Analyzed Customer Base
                </CardTitle>
                <div className="rounded-lg bg-primary/10 p-2 text-primary">
                  <Users className="h-4 w-4" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tracking-tight text-foreground">
                  {segmentData.total_customers.toLocaleString()}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">Unique buyer profiles clustered</p>
              </CardContent>
            </Card>

            <Card className="bg-card border-border">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Discovered Clusters (k)
                </CardTitle>
                <div className="rounded-lg bg-blue-500/10 p-2 text-blue-400">
                  <Layers className="h-4 w-4" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tracking-tight text-foreground">
                  {segmentData.optimal_k} Segments
                </div>
                <p className="mt-1 text-xs text-muted-foreground">Converged via k-means++</p>
              </CardContent>
            </Card>

            <Card className="bg-card border-border">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Cluster Separation Score
                </CardTitle>
                <div className="rounded-lg bg-emerald-500/10 p-2 text-emerald-400">
                  <Award className="h-4 w-4" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tracking-tight text-foreground">
                  {segmentData.silhouette_score.toFixed(3)}
                </div>
                <div className="mt-1 flex items-center gap-1.5">
                  <Badge
                    variant="outline"
                    className={`text-[10px] px-1.5 py-0 ${getSilhouetteGrade(segmentData.silhouette_score).color}`}
                  >
                    {getSilhouetteGrade(segmentData.silhouette_score).label}
                  </Badge>
                  <span className="text-[11px] text-muted-foreground">Silhouette Metric</span>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card border-border">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  PCA 2D Variance
                </CardTitle>
                <div className="rounded-lg bg-purple-500/10 p-2 text-purple-400">
                  <Activity className="h-4 w-4" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tracking-tight text-foreground">
                  {segmentData.pca_variance_explained}%
                </div>
                <p className="mt-1 text-xs text-muted-foreground">High-dimensional variance retained</p>
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
                <div className="p-1.5 rounded-md bg-amber-500/10 text-amber-400">
                  <Info className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-xs font-semibold text-foreground tracking-tight flex items-center gap-2">
                    Data Science Deep-Dive: Feature Normalization, $K$-Means Clustering, and PCA Projection
                  </h3>
                  <p className="text-[11px] text-muted-foreground">
                    Click to explore the mathematics, algorithms, and decision-support logic powering this engine.
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
                      <strong>Business:</strong> Blanket one-size-fits-all promotions erode profit margins. High-spending VIPs leave quietly while discount chasers consume support bandwidth.
                    </p>
                    <p>
                      <strong>Data Science:</strong> Map unlabelled customer records across 5 skewed behavioral dimensions ($R, F, M$, AOV, Lifespan) into dense, spherical, actionable micro-cohorts without supervision.
                    </p>
                  </div>

                  <div className="space-y-1.5 p-3 rounded-lg bg-muted/20 border border-border/40">
                    <p className="font-semibold text-foreground flex items-center gap-1.5">
                      <FileCode className="h-3.5 w-3.5 text-emerald-400" /> 2. Feature Standardization & Scaling
                    </p>
                    <p>
                      Financial and count variables (e.g., $M \in [\$10, \$100,000]$ vs $F \in [1, 50]$) possess massive scale asymmetry. We apply a two-step normalization pipeline:
                    </p>
                    <ul className="list-disc pl-4 space-y-0.5">
                      <li>Log-Transformation: x̃ = ln(1 + x) to compress severe right-skewed heavy tails.</li>
                      <li>StandardScaler: z = (x̃ - μ) / σ enforcing zero mean and unit variance across all features.</li>
                    </ul>
                  </div>

                  <div className="space-y-1.5 p-3 rounded-lg bg-muted/20 border border-border/40">
                    <p className="font-semibold text-foreground flex items-center gap-1.5">
                      <Compass className="h-3.5 w-3.5 text-blue-400" /> 3. K-Means Algorithm & Objective
                    </p>
                    <p>
                      Minimizes Within-Cluster Sum of Squares (Inertia):
                    </p>
                    <p className="font-mono text-[11px] bg-background/80 p-1.5 rounded border border-border/60 text-foreground">
                      J(C) = Σ (k=1 to K) Σ (x ∈ C_k) ||x - μ_k||²
                    </p>
                    <p>
                      We leverage <code>k-means++</code> seeding to select initial centroids proportionally to squared Euclidean distance, mitigating local-minima traps.
                    </p>
                  </div>

                  <div className="space-y-1.5 p-3 rounded-lg bg-muted/20 border border-border/40">
                    <p className="font-semibold text-foreground flex items-center gap-1.5">
                      <Award className="h-3.5 w-3.5 text-purple-400" /> 4. Evaluation: Silhouette & PCA
                    </p>
                    <p>
                      <strong>Silhouette Coefficient:</strong> Measures intra-cluster cohesion a(i) vs nearest-neighbor separation b(i): s(i) = (b(i) - a(i)) / max(a(i), b(i)). Values near 1 indicate crisp clusters.
                    </p>
                    <p>
                      <strong>PCA 2D Projection:</strong> Diagonalizes the covariance matrix Σ to project the 5-dimensional feature space onto the top 2 orthogonal eigenvectors, preserving maximal variance.
                    </p>
                  </div>
                </div>
              </CardContent>
            )}
          </Card>

          {/* Segment Persona Cards Grid */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-sm font-semibold text-foreground">Identified Customer Behavioral Personas</h2>
                <p className="text-xs text-muted-foreground">
                  Automated centroid profiling with revenue attribution and tactical playbooks
                </p>
              </div>
              <Badge variant="outline" className="text-xs font-normal">
                {segmentData.segments.length} Personas Defined
              </Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {segmentData.segments.map((segment) => (
                <Card
                  key={segment.cluster_id}
                  className="bg-card border-border hover:border-border/80 transition-all flex flex-col justify-between"
                  style={{ borderLeftColor: segment.color, borderLeftWidth: '4px' }}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span
                          className="h-2.5 w-2.5 rounded-full"
                          style={{ backgroundColor: segment.color }}
                        />
                        <CardTitle className="text-sm font-bold text-foreground">
                          {segment.label}
                        </CardTitle>
                      </div>
                      <Badge
                        variant="secondary"
                        className="text-xs font-semibold px-2 py-0.5"
                      >
                        {segment.customer_count.toLocaleString()} buyers ({segment.percentage}%)
                      </Badge>
                    </div>
                    <CardDescription className="text-xs mt-1 leading-snug">
                      {segment.description}
                    </CardDescription>
                  </CardHeader>

                  <CardContent className="space-y-4 pt-1">
                    {/* Metrics 4-cell grid */}
                    <div className="grid grid-cols-4 gap-2 p-2.5 rounded-lg bg-muted/20 border border-border/40 text-center">
                      <div>
                        <p className="text-[10px] text-muted-foreground font-medium uppercase">Avg Spend</p>
                        <p className="text-xs font-bold text-foreground mt-0.5">
                          ${segment.avg_monetary.toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] text-muted-foreground font-medium uppercase">Avg Orders</p>
                        <p className="text-xs font-bold text-foreground mt-0.5">
                          {segment.avg_frequency}x
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] text-muted-foreground font-medium uppercase">Recency</p>
                        <p className="text-xs font-bold text-foreground mt-0.5">
                          {segment.avg_recency}d
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] text-muted-foreground font-medium uppercase">Avg Ticket</p>
                        <p className="text-xs font-bold text-foreground mt-0.5">
                          ${segment.avg_order_value.toLocaleString()}
                        </p>
                      </div>
                    </div>

                    {/* Actionable Strategy Playbook */}
                    <div className="p-3 rounded-lg bg-primary/5 border border-primary/20 space-y-1">
                      <p className="text-[11px] font-semibold text-primary flex items-center gap-1.5">
                        <Target className="h-3 w-3" /> Recommended Strategy Playbook
                      </p>
                      <p className="text-xs text-foreground/90 leading-relaxed">
                        {segment.strategy_recommendation}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Interactive Visualizations Section with Tabs */}
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-2">
              <div className="flex items-center gap-2">
                <Button
                  variant={activeTab === 'pca' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setActiveTab('pca')}
                  className="text-xs h-8"
                >
                  <Activity className="mr-1.5 h-3.5 w-3.5" />
                  2D PCA Cluster Map
                </Button>
                <Button
                  variant={activeTab === 'diagnostics' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setActiveTab('diagnostics')}
                  className="text-xs h-8"
                >
                  <TrendingUp className="mr-1.5 h-3.5 w-3.5" />
                  Elbow & Silhouette Curve
                </Button>
                <Button
                  variant={activeTab === 'matrix' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setActiveTab('matrix')}
                  className="text-xs h-8"
                >
                  <Layers className="mr-1.5 h-3.5 w-3.5" />
                  Cohort Comparison Matrix
                </Button>
              </div>

              <span className="text-[11px] text-muted-foreground">
                Model: K-Means ({segmentData.optimal_k} centroids) • PCA: {segmentData.pca_variance_explained}% variance
              </span>
            </div>

            {/* TAB 1: 2D PCA Scatter Plot */}
            {activeTab === 'pca' && (
              <Card className="bg-card border-border">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-sm font-semibold text-foreground">
                        Principal Component Analysis (PCA) Customer Cluster Space
                      </CardTitle>
                      <CardDescription className="text-xs">
                        2D orthogonal projection of 5-dimensional customer vectors. Clustered dots indicate behavioral similarity.
                      </CardDescription>
                    </div>
                    <div className="flex flex-wrap items-center gap-3">
                      {segmentData.segments.map((seg) => (
                        <div key={seg.cluster_id} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                          <span
                            className="h-2.5 w-2.5 rounded-full shrink-0"
                            style={{ backgroundColor: seg.color }}
                          />
                          <span>{seg.label}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-4">
                  <div className="h-[420px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <ScatterChart margin={{ top: 20, right: 20, bottom: 25, left: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
                        <XAxis
                          type="number"
                          dataKey="x"
                          name="PC1"
                          stroke="#737373"
                          fontSize={10}
                          tickLine={false}
                          label={{
                            value: 'PC 1 (Purchase Frequency & Lifetime Spend)',
                            position: 'insideBottom',
                            offset: -15,
                            fill: '#737373',
                            fontSize: 11,
                          }}
                        />
                        <YAxis
                          type="number"
                          dataKey="y"
                          name="PC2"
                          stroke="#737373"
                          fontSize={10}
                          tickLine={false}
                          label={{
                            value: 'PC 2 (Recency & Inactivity)',
                            angle: -90,
                            position: 'insideLeft',
                            offset: 10,
                            fill: '#737373',
                            fontSize: 11,
                          }}
                        />
                        <Tooltip content={<CustomScatterTooltip />} />
                        <Scatter name="Customers" data={segmentData.pca_scatter}>
                          {segmentData.pca_scatter.map((entry, index) => {
                            const seg = segmentData.segments.find((s) => s.cluster_id === entry.cluster_id);
                            return (
                              <Cell
                                key={`cell-${index}`}
                                fill={seg?.color || '#3b82f6'}
                                fillOpacity={0.8}
                              />
                            );
                          })}
                        </Scatter>
                      </ScatterChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* TAB 2: Diagnostics & Elbow Curve */}
            {activeTab === 'diagnostics' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Inertia Elbow Curve */}
                <Card className="bg-card border-border">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-semibold text-foreground">
                      Elbow Curve (Within-Cluster Sum of Squares)
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Inertia reduction per additional cluster. The inflection point indicates optimal cluster economy.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-4">
                    <div className="h-[280px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={segmentData.elbow_curve} margin={{ top: 10, right: 20, bottom: 15, left: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
                          <XAxis
                            dataKey="k"
                            stroke="#737373"
                            fontSize={10}
                            tickLine={false}
                            label={{ value: 'Number of Clusters (k)', position: 'insideBottom', offset: -10, fill: '#737373', fontSize: 10 }}
                          />
                          <YAxis
                            stroke="#737373"
                            fontSize={10}
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={(v) => Math.round(v).toLocaleString()}
                          />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#171717',
                              borderColor: '#333',
                              borderRadius: '8px',
                              fontSize: '12px',
                            }}
                            formatter={(val: any) => [Number(val).toLocaleString(), 'Inertia']}
                            labelFormatter={(l) => `Cluster Count: k = ${l}`}
                          />
                          <Line
                            type="monotone"
                            dataKey="inertia"
                            stroke="#3b82f6"
                            strokeWidth={2.5}
                            dot={{ fill: '#3b82f6', r: 4 }}
                            activeDot={{ r: 6 }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                {/* Silhouette Score per k */}
                <Card className="bg-card border-border">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-semibold text-foreground">
                      Silhouette Coefficient by Cluster Count
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Cohesion vs. Separation metric. Peaks at the most mathematically distinct cluster configuration.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-4">
                    <div className="h-[280px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={segmentData.elbow_curve} margin={{ top: 10, right: 20, bottom: 15, left: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
                          <XAxis
                            dataKey="k"
                            stroke="#737373"
                            fontSize={10}
                            tickLine={false}
                            label={{ value: 'Number of Clusters (k)', position: 'insideBottom', offset: -10, fill: '#737373', fontSize: 10 }}
                          />
                          <YAxis
                            stroke="#737373"
                            fontSize={10}
                            tickLine={false}
                            axisLine={false}
                            domain={[0, 1]}
                            tickFormatter={(v) => v.toFixed(2)}
                          />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#171717',
                              borderColor: '#333',
                              borderRadius: '8px',
                              fontSize: '12px',
                            }}
                            formatter={(val: any) => [Number(val).toFixed(3), 'Silhouette Score']}
                            labelFormatter={(l) => `Cluster Count: k = ${l}`}
                          />
                          <Line
                            type="monotone"
                            dataKey="silhouette"
                            stroke="#10b981"
                            strokeWidth={2.5}
                            dot={{ fill: '#10b981', r: 4 }}
                            activeDot={{ r: 6 }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* TAB 3: Segment Comparison Matrix */}
            {activeTab === 'matrix' && (
              <Card className="bg-card border-border overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-muted/40 text-muted-foreground uppercase text-[10px] tracking-wider border-b border-border">
                      <tr>
                        <th className="px-4 py-3">Cluster Persona</th>
                        <th className="px-4 py-3 text-right">Population</th>
                        <th className="px-4 py-3 text-right">Avg Spend</th>
                        <th className="px-4 py-3 text-right">Avg Orders</th>
                        <th className="px-4 py-3 text-right">Avg Recency</th>
                        <th className="px-4 py-3 text-right">Avg Ticket (AOV)</th>
                        <th className="px-4 py-3">Marketing Priority</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/50">
                      {segmentData.segments.map((seg) => (
                        <tr key={seg.cluster_id} className="hover:bg-muted/20 transition-colors">
                          <td className="px-4 py-3 font-medium text-foreground flex items-center gap-2">
                            <span
                              className="h-2.5 w-2.5 rounded-full shrink-0"
                              style={{ backgroundColor: seg.color }}
                            />
                            {seg.label}
                          </td>
                          <td className="px-4 py-3 text-right font-medium text-foreground">
                            {seg.customer_count.toLocaleString()}{' '}
                            <span className="text-muted-foreground font-normal">({seg.percentage}%)</span>
                          </td>
                          <td className="px-4 py-3 text-right font-semibold text-emerald-400">
                            ${seg.avg_monetary.toLocaleString()}
                          </td>
                          <td className="px-4 py-3 text-right text-foreground">
                            {seg.avg_frequency}x
                          </td>
                          <td className="px-4 py-3 text-right text-foreground">
                            {seg.avg_recency} days
                          </td>
                          <td className="px-4 py-3 text-right text-foreground">
                            ${seg.avg_order_value.toLocaleString()}
                          </td>
                          <td className="px-4 py-3 text-muted-foreground max-w-xs truncate">
                            {seg.strategy_recommendation}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}
          </div>
        </>
      )}
      </>
      )}
    </div>
  );
}
