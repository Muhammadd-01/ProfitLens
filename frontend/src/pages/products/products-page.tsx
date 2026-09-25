import { useState, useEffect } from 'react';
import {
  Package,
  Sparkles,
  TrendingUp,
  DollarSign,
  Layers,
  Award,
  RefreshCw,
  Search,
  Sliders,
  Database,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  ArrowUpRight,
  ArrowDownRight,
  Target,
  CheckCircle2,
  PieChart as PieIcon,
  Tag,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/common/empty-state';
import { useDatasetStore } from '@/stores/dataset-store';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import type {
  ProductIntelligenceResponse,
  ProductBCGItem,
  Dataset,
} from '@/types';
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
  ReferenceLine,
  Legend,
} from 'recharts';

export function ProductsPage() {
  const { datasets, activeDataset, setActiveDataset, setDatasets } = useDatasetStore();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<ProductIntelligenceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [quadrantFilter, setQuadrantFilter] = useState<string>('all');
  const [paretoFilter, setParetoFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [showPedagogy, setShowPedagogy] = useState(false);

  useEffect(() => {
    if (datasets.length === 0) {
      loadDatasets();
    } else if (activeDataset?.id) {
      loadProductIntelligence(activeDataset.id);
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
        loadProductIntelligence(first.id);
      } else {
        setLoading(false);
      }
    } catch {
      setLoading(false);
    }
  };

  const loadProductIntelligence = async (datasetId: string) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get<ProductIntelligenceResponse>(
        `/analytics/${datasetId}/products/intelligence`
      );
      setData(resp.data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Unable to load product intelligence. Please ensure product_id, revenue, and order_date columns are mapped.';
      setError(msg);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  // Distinct categories
  const categories = Array.from(
    new Set((data?.products || []).map((p) => p.category || 'General'))
  ).sort();

  // Filtered products
  const filteredProducts = (data?.products || []).filter((p) => {
    if (quadrantFilter !== 'all' && p.bcg_category !== quadrantFilter) return false;
    if (paretoFilter !== 'all' && p.pareto_class !== paretoFilter) return false;
    if (categoryFilter !== 'all' && (p.category || 'General') !== categoryFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchId = p.product_id.toLowerCase().includes(q);
      const matchName = (p.product_name || '').toLowerCase().includes(q);
      return matchId || matchName;
    }
    return true;
  });

  const getBcgBadge = (quadrant: string) => {
    switch (quadrant) {
      case 'star':
        return (
          <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 font-medium">
            ★ Star
          </Badge>
        );
      case 'cash_cow':
        return (
          <Badge className="bg-blue-500/10 text-blue-600 border-blue-500/20 font-medium">
            ◈ Cash Cow
          </Badge>
        );
      case 'question_mark':
        return (
          <Badge className="bg-amber-500/10 text-amber-600 border-amber-500/20 font-medium">
            ? Question Mark
          </Badge>
        );
      default:
        return (
          <Badge className="bg-rose-500/10 text-rose-600 border-rose-500/20 font-medium">
            ✕ Dog
          </Badge>
        );
    }
  };

  const getParetoBadge = (pClass: string) => {
    switch (pClass) {
      case 'A':
        return (
          <Badge variant="outline" className="border-emerald-500/30 text-emerald-600 bg-emerald-500/5">
            Class A (Top 80%)
          </Badge>
        );
      case 'B':
        return (
          <Badge variant="outline" className="border-amber-500/30 text-amber-600 bg-amber-500/5">
            Class B (Next 15%)
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" className="border-slate-500/30 text-slate-600 bg-slate-500/5">
            Class C (Tail 5%)
          </Badge>
        );
    }
  };

  // Color mapper for BCG scatter
  const getBcgColor = (cat: string) => {
    if (cat === 'star') return '#10b981'; // emerald
    if (cat === 'cash_cow') return '#3b82f6'; // blue
    if (cat === 'question_mark') return '#f59e0b'; // amber
    return '#f43f5e'; // rose
  };

  // Prepare BCG scatter chart points
  const bcgScatterData = (data?.products || []).map((p) => ({
    x: p.relative_market_share,
    y: p.growth_rate_pct,
    revenue: p.revenue,
    id: p.product_id,
    name: p.product_name || p.product_id,
    quadrant: p.bcg_category,
    category: p.category || 'General',
  }));

  // Pareto chart data: take top 20 or all if fewer
  const paretoChartData = (data?.pareto_points || []).slice(0, 25).map((pt) => ({
    name: pt.product_name.length > 15 ? `${pt.product_name.substring(0, 15)}...` : pt.product_name,
    fullName: pt.product_name,
    revenue: pt.revenue,
    cumulativePct: pt.cumulative_percentage,
    isInTop80: pt.is_in_top_80,
  }));

  if (datasets.length === 0 && !loading) {
    return (
      <div className="p-8">
        <EmptyState
          icon={Package}
          title="No Datasets Uploaded"
          description="Upload an e-commerce or ERP transaction dataset to analyze product catalog performance and BCG matrix."
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
            <div className="p-2.5 rounded-xl bg-primary/10 text-primary">
              <Package className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Product Performance & BCG Matrix</h1>
              <p className="text-sm text-muted-foreground">
                Strategic SKU portfolio intelligence, BCG Growth-Share classification, and Pareto 80/20 distribution.
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
                  loadProductIntelligence(ds.id);
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

          <Button
            onClick={() => activeDataset && loadProductIntelligence(activeDataset.id)}
            disabled={loading || !activeDataset}
            variant="outline"
            className="gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>

          <Button
            variant="outline"
            onClick={() => setShowPedagogy(!showPedagogy)}
            className="gap-2 text-xs"
          >
            <HelpCircle className="w-4 h-4 text-blue-500" />
            Framework Deep Dive
            {showPedagogy ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </Button>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
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
              Educational Masterclass: BCG Growth-Share Matrix & Pareto 80/20 Distribution
            </div>
            <CardDescription className="text-xs sm:text-sm">
              Mathematical foundations of SKU rationalization, relative market share, and revenue power-law concentration.
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
                  Retail catalogs suffer from "SKU bloat": thousands of low-velocity products absorb warehouse space, tie up
                  working capital, and confuse buyers, while 80% of revenue is generated by a handful of core winners.
                  Merchants need empirical rules to decide which products to scale, harvest, or liquidate.
                </p>
              </div>

              <div className="p-4 rounded-lg bg-card border space-y-2">
                <h4 className="font-semibold text-foreground flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-500" />
                  2. The Data Science Problem
                </h4>
                <p className="text-muted-foreground text-xs leading-relaxed">
                  We formulate product intelligence as a multi-criteria portfolio matrix combining <em>period-over-period sales momentum</em>
                  with <em>relative market dominance</em>. Products are mapped onto a 2D coordinate space and segmented into actionable
                  merchandising archetypes.
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
                  <p className="font-mono font-semibold text-primary">BCG Growth-Share Coordinates:</p>
                  <p className="text-muted-foreground">
                    Developed by the Boston Consulting Group. For each product <code className="font-mono">p</code>:
                  </p>
                  <div className="font-mono bg-background p-2 rounded border text-center text-xs space-y-1">
                    <div>{`RMS_p = Revenue_p / max_{q in Category}(Revenue_q)`}</div>
                    <div>{`Growth_p = ((Revenue_{recent} - Revenue_{prior}) / Revenue_{prior}) * 100%`}</div>
                  </div>
                  <p className="text-muted-foreground">
                    Relative Market Share (RMS) evaluates product leadership against category champions.
                  </p>
                </div>

                <div className="space-y-2 bg-muted/40 p-3 rounded-md">
                  <p className="font-mono font-semibold text-primary">Pareto Cumulative Distribution & ABC Stratification:</p>
                  <p className="text-muted-foreground">
                    Products are ranked descending by revenue <code className="font-mono">R_(1) &ge; R_(2) &ge; ... &ge; R_(N)</code>:
                  </p>
                  <div className="font-mono bg-background p-2 rounded border text-center text-xs">
                    {`R_cum(i) = [Sum_{j=1}^i R_{(j)} / Sum_{j=1}^N R_j] * 100%`}
                  </div>
                  <p className="text-muted-foreground">
                    Class A comprises the "Vital Few" generating up to 80% of revenue. Class B generates the next 15%, and Class C represents the long-tail 5%.
                  </p>
                </div>
              </div>
            </div>

            {/* Strategic Decision Matrix */}
            <div className="p-4 rounded-lg bg-card border space-y-2">
              <h4 className="font-semibold text-foreground flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                4. Capital Allocation Across Quadrants
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 text-xs text-muted-foreground">
                <div className="p-2.5 rounded bg-emerald-500/10 border border-emerald-500/20">
                  <strong className="text-emerald-600 block mb-1">Stars</strong>
                  High growth, dominant share. Reinvest advertising and protect supply chain buffers.
                </div>
                <div className="p-2.5 rounded bg-blue-500/10 border border-blue-500/20">
                  <strong className="text-blue-600 block mb-1">Cash Cows</strong>
                  Low growth, dominant share. Harvest cash flow with minimal ad spend to fund Stars.
                </div>
                <div className="p-2.5 rounded bg-amber-500/10 border border-amber-500/20">
                  <strong className="text-amber-600 block mb-1">Question Marks</strong>
                  High market growth, low share. Test promotional pricing to build scale or divest.
                </div>
                <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/20">
                  <strong className="text-rose-600 block mb-1">Dogs</strong>
                  Low growth, low share. Liquidate inventory via bundle discounts and discontinue SKU.
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading state */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center space-y-4">
          <RefreshCw className="w-8 h-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Aggregating SKU volumes, computing BCG matrices, and sorting Pareto curves...</p>
        </div>
      ) : data ? (
        <>
          {/* Executive KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="border-border">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground">Total Catalog Size</span>
                  <div className="p-2 rounded-lg bg-primary/10 text-primary">
                    <Package className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-2xl font-bold tracking-tight">
                    {data.total_products}{' '}
                    <span className="text-xs font-normal text-muted-foreground">SKUs</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {data.total_units_sold.toLocaleString()} units sold across catalog
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground">Product Revenue</span>
                  <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-600">
                    <DollarSign className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-2xl font-bold tracking-tight text-emerald-600">
                    ${data.total_revenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Avg ${data.avg_product_revenue.toFixed(2)} generated per SKU
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground">Lead Category</span>
                  <div className="p-2 rounded-lg bg-blue-500/10 text-blue-600">
                    <Award className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-2xl font-bold tracking-tight truncate" title={data.top_performing_category || 'N/A'}>
                    {data.top_performing_category || 'General'}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Highest revenue contributing product category
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground">Vital 80% Cohort</span>
                  <div className="p-2 rounded-lg bg-amber-500/10 text-amber-600">
                    <PieIcon className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-2xl font-bold tracking-tight">
                    {data.pareto_points.filter((p) => p.is_in_top_80).length}{' '}
                    <span className="text-xs font-normal text-muted-foreground">
                      / {data.total_products} SKUs
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {((data.pareto_points.filter((p) => p.is_in_top_80).length / Math.max(1, data.total_products)) * 100).toFixed(1)}% of SKUs deliver 80% of revenue
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* BCG Matrix Quadrant Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="border-emerald-500/20 bg-emerald-500/5">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">★</span>
                    <span className="font-semibold text-emerald-600 text-sm">Stars</span>
                  </div>
                  <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 border-emerald-500/30 text-[10px]">
                    High Growth · High Share
                  </Badge>
                </div>
                <div className="mt-3">
                  <div className="text-xl font-bold text-foreground">
                    {data.bcg_distribution.stars_count} SKUs
                  </div>
                  <div className="text-xs font-medium text-emerald-600 mt-0.5">
                    ${data.bcg_distribution.stars_revenue.toLocaleString()} (
                    {data.total_revenue > 0 ? ((data.bcg_distribution.stars_revenue / data.total_revenue) * 100).toFixed(1) : 0}%)
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-2">
                    Reinvest cash flow to defend market dominance and scale inventory.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-blue-500/20 bg-blue-500/5">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">◈</span>
                    <span className="font-semibold text-blue-600 text-sm">Cash Cows</span>
                  </div>
                  <Badge variant="outline" className="bg-blue-500/10 text-blue-600 border-blue-500/30 text-[10px]">
                    Low Growth · High Share
                  </Badge>
                </div>
                <div className="mt-3">
                  <div className="text-xl font-bold text-foreground">
                    {data.bcg_distribution.cash_cows_count} SKUs
                  </div>
                  <div className="text-xs font-medium text-blue-600 mt-0.5">
                    ${data.bcg_distribution.cash_cows_revenue.toLocaleString()} (
                    {data.total_revenue > 0 ? ((data.bcg_distribution.cash_cows_revenue / data.total_revenue) * 100).toFixed(1) : 0}%)
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-2">
                    Staple profit generators. Protect gross margins without excess marketing.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-amber-500/20 bg-amber-500/5">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">?</span>
                    <span className="font-semibold text-amber-600 text-sm">Question Marks</span>
                  </div>
                  <Badge variant="outline" className="bg-amber-500/10 text-amber-600 border-amber-500/30 text-[10px]">
                    High Growth · Low Share
                  </Badge>
                </div>
                <div className="mt-3">
                  <div className="text-xl font-bold text-foreground">
                    {data.bcg_distribution.question_marks_count} SKUs
                  </div>
                  <div className="text-xs font-medium text-amber-600 mt-0.5">
                    ${data.bcg_distribution.question_marks_revenue.toLocaleString()} (
                    {data.total_revenue > 0 ? ((data.bcg_distribution.question_marks_revenue / data.total_revenue) * 100).toFixed(1) : 0}%)
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-2">
                    Emerging demand with trailing share. Selectively invest or divest.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-rose-500/20 bg-rose-500/5">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">✕</span>
                    <span className="font-semibold text-rose-600 text-sm">Dogs</span>
                  </div>
                  <Badge variant="outline" className="bg-rose-500/10 text-rose-600 border-rose-500/30 text-[10px]">
                    Low Growth · Low Share
                  </Badge>
                </div>
                <div className="mt-3">
                  <div className="text-xl font-bold text-foreground">
                    {data.bcg_distribution.dogs_count} SKUs
                  </div>
                  <div className="text-xs font-medium text-rose-600 mt-0.5">
                    ${data.bcg_distribution.dogs_revenue.toLocaleString()} (
                    {data.total_revenue > 0 ? ((data.bcg_distribution.dogs_revenue / data.total_revenue) * 100).toFixed(1) : 0}%)
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-2">
                    Cash drain and slow inventory turns. Discount and phase out SKUs.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Charts Row: BCG Scatter Plot + Pareto Cumulative Curve */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* BCG Growth-Share Scatter Chart */}
            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <Target className="w-4 h-4 text-primary" />
                  BCG Growth-Share Matrix Map
                </CardTitle>
                <CardDescription className="text-xs">
                  Scatter coordinates: Relative Market Share (X) vs Sales Growth Rate (Y).
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[300px] w-full pt-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                      <XAxis
                        type="number"
                        dataKey="x"
                        name="Relative Market Share"
                        domain={[0, 1.1]}
                        tick={{ fontSize: 11 }}
                        tickLine={false}
                      />
                      <YAxis
                        type="number"
                        dataKey="y"
                        name="Growth Rate (%)"
                        tickFormatter={(val) => `${val}%`}
                        tick={{ fontSize: 11 }}
                        tickLine={false}
                      />
                      <ReferenceLine x={0.4} stroke="#94a3b8" strokeDasharray="3 3" />
                      <ReferenceLine y={0.0} stroke="#94a3b8" strokeDasharray="3 3" />
                      <Tooltip
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const pt = payload[0].payload;
                            return (
                              <div className="p-3 bg-card border rounded-lg shadow-xl text-xs space-y-1">
                                <p className="font-semibold text-foreground">{pt.name}</p>
                                <p className="text-muted-foreground">SKU: {pt.id} | {pt.category}</p>
                                <p className="font-medium text-foreground">Revenue: ${pt.revenue.toFixed(2)}</p>
                                <p className="text-muted-foreground">Share: {(pt.x * 100).toFixed(1)}% | Growth: {pt.y.toFixed(1)}%</p>
                                <div className="pt-1">
                                  {getBcgBadge(pt.quadrant)}
                                </div>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Scatter name="Products" data={bcgScatterData}>
                        {bcgScatterData.map((entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={getBcgColor(entry.quadrant)}
                            opacity={0.85}
                            r={6}
                          />
                        ))}
                      </Scatter>
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Pareto 80/20 Cumulative Distribution Chart */}
            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <PieIcon className="w-4 h-4 text-primary" />
                  Pareto 80/20 Cumulative Concentration
                </CardTitle>
                <CardDescription className="text-xs">
                  SKUs sorted by descending revenue with cumulative percentage trajectory.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[300px] w-full pt-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={paretoChartData} margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                      <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={1} angle={-35} textAnchor="end" height={50} />
                      <YAxis yAxisId="left" tickFormatter={(v) => `$${v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}`} tick={{ fontSize: 11 }} />
                      <YAxis yAxisId="right" orientation="right" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} />
                      <Tooltip
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const pt = payload[0].payload;
                            return (
                              <div className="p-3 bg-card border rounded-lg shadow-xl text-xs space-y-1">
                                <p className="font-semibold text-foreground">{pt.fullName}</p>
                                <p className="text-muted-foreground">Revenue: ${pt.revenue.toFixed(2)}</p>
                                <p className="font-mono text-primary">Cumulative Share: {pt.cumulativePct.toFixed(1)}%</p>
                                <Badge variant="outline" className={`text-[10px] mt-1 ${pt.isInTop80 ? 'bg-emerald-500/10 text-emerald-600' : 'bg-slate-500/10 text-slate-600'}`}>
                                  {pt.isInTop80 ? 'Class A (Vital 80%)' : 'Tail Cohort'}
                                </Badge>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <ReferenceLine yAxisId="right" y={80} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: '80% Cutoff', position: 'insideTopLeft', fill: '#f59e0b', fontSize: 10 }} />
                      <Bar yAxisId="left" dataKey="revenue" fill="#3b82f6" radius={[4, 4, 0, 0]} opacity={0.8} />
                      <Line yAxisId="right" type="monotone" dataKey="cumulativePct" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Product Catalog & Action Plan Table */}
          <Card className="border-border">
            <CardHeader className="pb-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <CardTitle className="text-base font-semibold flex items-center gap-2">
                    <Layers className="w-4 h-4 text-primary" />
                    Product Performance Catalog & Action Guide
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Full portfolio inventory with empirical classifications and merchandising recommendations.
                  </CardDescription>
                </div>

                {/* Filters */}
                <div className="flex flex-wrap items-center gap-2.5">
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted-foreground" />
                    <input
                      type="text"
                      placeholder="Search SKU or name..."
                      className="pl-8 pr-3 py-1.5 text-xs bg-muted/50 border rounded-lg focus:outline-none focus:ring-1 focus:ring-primary w-48"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>

                  <select
                    className="text-xs bg-muted/50 border rounded-lg px-2.5 py-1.5 focus:outline-none cursor-pointer"
                    value={quadrantFilter}
                    onChange={(e) => setQuadrantFilter(e.target.value)}
                  >
                    <option value="all">All Quadrants</option>
                    <option value="star">★ Stars</option>
                    <option value="cash_cow">◈ Cash Cows</option>
                    <option value="question_mark">? Question Marks</option>
                    <option value="dog">✕ Dogs</option>
                  </select>

                  <select
                    className="text-xs bg-muted/50 border rounded-lg px-2.5 py-1.5 focus:outline-none cursor-pointer"
                    value={paretoFilter}
                    onChange={(e) => setParetoFilter(e.target.value)}
                  >
                    <option value="all">All Pareto Classes</option>
                    <option value="A">Class A (Top 80%)</option>
                    <option value="B">Class B (Next 15%)</option>
                    <option value="C">Class C (Tail 5%)</option>
                  </select>

                  {categories.length > 1 && (
                    <select
                      className="text-xs bg-muted/50 border rounded-lg px-2.5 py-1.5 focus:outline-none cursor-pointer"
                      value={categoryFilter}
                      onChange={(e) => setCategoryFilter(e.target.value)}
                    >
                      <option value="all">All Categories</option>
                      {categories.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  )}
                </div>
              </div>
            </CardHeader>

            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-muted/50 border-y text-muted-foreground uppercase tracking-wider text-[10px]">
                    <tr>
                      <th className="py-3 px-4">Product Name & SKU</th>
                      <th className="py-3 px-4">Category</th>
                      <th className="py-3 px-4">Revenue</th>
                      <th className="py-3 px-4">Units Sold</th>
                      <th className="py-3 px-4">Avg Price</th>
                      <th className="py-3 px-4">Growth Rate</th>
                      <th className="py-3 px-4">BCG Quadrant</th>
                      <th className="py-3 px-4">Pareto Class</th>
                      <th className="py-3 px-4">Strategic Action Plan</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {filteredProducts.length === 0 ? (
                      <tr>
                        <td colSpan={9} className="text-center py-8 text-muted-foreground">
                          No products match the selected filters.
                        </td>
                      </tr>
                    ) : (
                      filteredProducts.map((p) => (
                        <tr key={p.product_id} className="hover:bg-muted/30 transition-colors">
                          <td className="py-3 px-4">
                            <div className="font-semibold text-foreground">{p.product_name || p.product_id}</div>
                            <div className="text-[11px] text-muted-foreground font-mono">{p.product_id}</div>
                          </td>
                          <td className="py-3 px-4 text-muted-foreground">
                            {p.category || 'General'}
                          </td>
                          <td className="py-3 px-4 font-semibold text-foreground">
                            ${p.revenue.toFixed(2)}
                          </td>
                          <td className="py-3 px-4 text-muted-foreground">
                            {p.units_sold.toLocaleString()}
                          </td>
                          <td className="py-3 px-4 text-muted-foreground font-mono">
                            ${p.avg_price.toFixed(2)}
                          </td>
                          <td className="py-3 px-4">
                            <div className={`flex items-center gap-1 font-medium ${p.growth_rate_pct >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                              {p.growth_rate_pct >= 0 ? (
                                <ArrowUpRight className="w-3.5 h-3.5" />
                              ) : (
                                <ArrowDownRight className="w-3.5 h-3.5" />
                              )}
                              <span>{p.growth_rate_pct >= 0 ? `+${p.growth_rate_pct.toFixed(1)}%` : `${p.growth_rate_pct.toFixed(1)}%`}</span>
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            {getBcgBadge(p.bcg_category)}
                          </td>
                          <td className="py-3 px-4">
                            {getParetoBadge(p.pareto_class)}
                          </td>
                          <td className="py-3 px-4 max-w-xs">
                            <p className="text-[11px] text-muted-foreground leading-snug">
                              {p.recommendation}
                            </p>
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
