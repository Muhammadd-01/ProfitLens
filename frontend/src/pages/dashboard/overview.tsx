import { useState, useEffect } from 'react';
import {
  DollarSign,
  ShoppingCart,
  Users,
  TrendingUp,
  Database,
  Calendar,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  Award,
  Sparkles,
  Package,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/common/empty-state';
import { TableSkeleton } from '@/components/common/loading-skeleton';
import { useDatasetStore } from '@/stores/dataset-store';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import type { ExecutiveDashboardSummary, Dataset } from '@/types';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from 'recharts';

interface KPICardProps {
  title: string;
  value: string;
  change?: number | null;
  icon: React.ElementType;
  subtext?: string;
}

function KPICard({ title, value, change, icon: Icon, subtext }: KPICardProps) {
  const isPositive = change !== undefined && change !== null && change >= 0;
  const isNegative = change !== undefined && change !== null && change < 0;

  return (
    <Card className="bg-card border-border transition-colors hover:border-primary/40">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          {title}
        </CardTitle>
        <div className="rounded-lg bg-primary/10 p-2 text-primary">
          <Icon className="h-4 w-4" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold tracking-tight text-foreground">{value}</div>
        <div className="mt-2 flex items-center justify-between text-xs">
          {change !== undefined && change !== null ? (
            <div
              className={`flex items-center font-medium ${
                isPositive ? 'text-emerald-400' : isNegative ? 'text-rose-400' : 'text-muted-foreground'
              }`}
            >
              {isPositive ? (
                <ArrowUpRight className="mr-0.5 h-3.5 w-3.5" />
              ) : isNegative ? (
                <ArrowDownRight className="mr-0.5 h-3.5 w-3.5" />
              ) : null}
              <span>
                {isPositive ? '+' : ''}
                {change.toFixed(1)}%
              </span>
              <span className="text-muted-foreground ml-1 font-normal">vs prior period</span>
            </div>
          ) : (
            <span className="text-muted-foreground font-normal">Base period benchmark</span>
          )}
          {subtext && <span className="text-muted-foreground text-[11px]">{subtext}</span>}
        </div>
      </CardContent>
    </Card>
  );
}

export function OverviewPage() {
  const { datasets, activeDataset, setActiveDataset } = useDatasetStore();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState<ExecutiveDashboardSummary | null>(null);
  const [granularity, setGranularity] = useState<'daily' | 'monthly'>('daily');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (activeDataset?.id) {
      loadDashboard(activeDataset.id);
    } else if (datasets.length > 0) {
      setActiveDataset(datasets[0]);
    } else {
      setLoading(false);
    }
  }, [activeDataset?.id, datasets.length]);

  const loadDashboard = async (datasetId: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<ExecutiveDashboardSummary>(`/analytics/${datasetId}/summary`);
      setDashboardData(response.data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Unable to load analytics. Please ensure the dataset is mapped and cleaned.';
      setError(msg);
      setDashboardData(null);
    } finally {
      setLoading(false);
    }
  };

  if (!activeDataset && datasets.length === 0) {
    return (
      <EmptyState
        icon={Database}
        title="No business datasets yet"
        description="Upload your store transactions or sales ledger to calculate executive KPIs, revenue trajectories, and Pareto category distributions."
        actionLabel="Upload First Dataset"
        onAction={() => navigate('/dashboard/datasets')}
      />
    );
  }

  const timeSeriesData =
    granularity === 'monthly'
      ? dashboardData?.time_series_monthly || []
      : dashboardData?.time_series_daily || [];

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Top Header & Dataset Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Executive Overview</h1>
            <Badge variant="outline" className="text-xs bg-primary/10 text-primary border-primary/20">
              Business Intelligence
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Top-level financial indicators, period-over-period momentum, and category Pareto distributions
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
            onClick={() => activeDataset && loadDashboard(activeDataset.id)}
            disabled={loading}
            className="text-xs flex items-center gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {loading ? (
        <TableSkeleton rows={8} />
      ) : error ? (
        <Card className="border-border bg-card p-8 text-center">
          <div className="max-w-md mx-auto space-y-3">
            <div className="mx-auto w-12 h-12 rounded-full bg-amber-500/10 flex items-center justify-center text-amber-400">
              <Sparkles className="h-6 w-6" />
            </div>
            <h3 className="text-base font-semibold text-foreground">Dataset Needs Setup</h3>
            <p className="text-xs text-muted-foreground">{error}</p>
            <Button
              size="sm"
              onClick={() => navigate('/dashboard/datasets')}
              className="mt-2 text-xs bg-primary text-primary-foreground"
            >
              Configure Schema & Cleaning
            </Button>
          </div>
        </Card>
      ) : dashboardData ? (
        <div className="space-y-8">
          {/* Observation Period Banner */}
          <div className="flex items-center justify-between px-4 py-2.5 rounded-lg border border-border bg-secondary/30 text-xs">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Calendar className="h-4 w-4 text-primary" />
              <span>
                Observation Range:{' '}
                <strong className="text-foreground">{dashboardData.observation_period.start_date}</strong> to{' '}
                <strong className="text-foreground">{dashboardData.observation_period.end_date}</strong>
              </span>
              <span className="text-muted-foreground/60">•</span>
              <span>
                Span: <strong className="text-foreground">{dashboardData.observation_period.total_days} days</strong>
              </span>
            </div>
            <Badge variant="outline" className="text-[11px] font-mono">
              Dataset: {activeDataset?.name}
            </Badge>
          </div>

          {/* Hero KPI Cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KPICard
              title="Total Revenue"
              value={`$${dashboardData.kpis.total_revenue.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}`}
              change={dashboardData.kpis.revenue_change_pct}
              icon={DollarSign}
            />
            <KPICard
              title="Total Orders"
              value={dashboardData.kpis.total_orders.toLocaleString()}
              change={dashboardData.kpis.orders_change_pct}
              icon={ShoppingCart}
            />
            <KPICard
              title="Active Customers"
              value={dashboardData.kpis.total_customers.toLocaleString()}
              change={dashboardData.kpis.customers_change_pct}
              icon={Users}
            />
            <KPICard
              title="Average Order Value"
              value={`$${dashboardData.kpis.avg_order_value.toFixed(2)}`}
              change={dashboardData.kpis.aov_change_pct}
              icon={TrendingUp}
              subtext="Spend / Order"
            />
          </div>

          {/* Main Charts Grid */}
          <div className="grid gap-6 lg:grid-cols-3">
            {/* 1. Revenue Trajectory (2 Cols) */}
            <Card className="bg-card border-border lg:col-span-2">
              <CardHeader className="pb-2">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <CardTitle className="text-base flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-primary" />
                      Revenue Trajectory
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Historical sales progression with periodic revenue totals
                    </CardDescription>
                  </div>
                  <div className="flex items-center rounded-lg bg-secondary p-0.5 border border-border text-xs">
                    <button
                      onClick={() => setGranularity('daily')}
                      className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                        granularity === 'daily'
                          ? 'bg-card text-foreground shadow-sm'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      Daily
                    </button>
                    <button
                      onClick={() => setGranularity('monthly')}
                      className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                        granularity === 'monthly'
                          ? 'bg-card text-foreground shadow-sm'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      Monthly
                    </button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-4">
                <div className="h-[300px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={timeSeriesData}
                      margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                    >
                      <defs>
                        <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--color-primary, #6366f1)" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="var(--color-primary, #6366f1)" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
                      <XAxis
                        dataKey="date"
                        stroke="#737373"
                        fontSize={10}
                        tickLine={false}
                        tickFormatter={(val) => {
                          if (granularity === 'daily' && val.length >= 10) {
                            return val.slice(5); // MM-DD
                          }
                          return val;
                        }}
                      />
                      <YAxis
                        stroke="#737373"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(val) => `$${(val / 1000).toFixed(0)}k`}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#171717',
                          borderColor: '#333',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                        formatter={(value: any) => [`$${Number(value).toLocaleString()}`, 'Revenue']}
                        labelFormatter={(label) => `Period: ${label}`}
                      />
                      <Area
                        type="monotone"
                        dataKey="revenue"
                        stroke="var(--color-primary, #6366f1)"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#revenueGradient)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* 2. Category Distribution & Pareto 80/20 (1 Col) */}
            <Card className="bg-card border-border">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Award className="h-4 w-4 text-amber-400" />
                    Category Revenue Share
                  </CardTitle>
                  <Badge variant="outline" className="text-[10px] text-amber-400 border-amber-500/20">
                    Pareto 80/20
                  </Badge>
                </div>
                <CardDescription className="text-xs">
                  Categories highlighted in gold drive 80% of total company revenue
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-2">
                {dashboardData.categories.length === 0 ? (
                  <div className="h-[300px] flex items-center justify-center text-xs text-muted-foreground">
                    No category data available
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="h-[180px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={dashboardData.categories}
                          layout="vertical"
                          margin={{ top: 5, right: 10, left: 20, bottom: 5 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#262626" horizontal={false} />
                          <XAxis
                            type="number"
                            stroke="#737373"
                            fontSize={10}
                            tickFormatter={(val) => `${val}%`}
                          />
                          <YAxis
                            type="category"
                            dataKey="category"
                            stroke="#737373"
                            fontSize={10}
                            tickLine={false}
                            axisLine={false}
                          />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#171717',
                              borderColor: '#333',
                              borderRadius: '8px',
                              fontSize: '12px',
                            }}
                            formatter={(value: any, name: any, item: any) => [
                              `$${item.payload.revenue.toLocaleString()} (${value}%)`,
                              'Share',
                            ]}
                          />
                          <Bar dataKey="percentage" radius={[0, 4, 4, 0]}>
                            {dashboardData.categories.map((entry, index) => (
                              <Cell
                                key={`cell-${index}`}
                                fill={entry.is_pareto_80 ? '#f59e0b' : '#3b82f6'}
                              />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>

                    {/* Category Breakdown Table */}
                    <div className="space-y-1.5 pt-2 border-t border-border">
                      {dashboardData.categories.slice(0, 4).map((c) => (
                        <div
                          key={c.category}
                          className="flex items-center justify-between text-xs p-1.5 rounded hover:bg-secondary/30 transition-colors"
                        >
                          <div className="flex items-center gap-2">
                            <div
                              className={`w-2 h-2 rounded-full ${
                                c.is_pareto_80 ? 'bg-amber-400' : 'bg-sky-400'
                              }`}
                            />
                            <span className="font-medium text-foreground">{c.category}</span>
                            {c.is_pareto_80 && (
                              <span className="text-[10px] text-amber-400/90 font-semibold uppercase">
                                Pareto Core
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 font-mono text-muted-foreground">
                            <span>${c.revenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                            <span className="w-10 text-right font-semibold text-foreground">
                              {c.percentage}%
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Top Products Performance Table */}
          {dashboardData.top_products.length > 0 && (
            <Card className="bg-card border-border">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Package className="h-4 w-4 text-primary" />
                      Top Revenue-Generating Products
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Highest grossing SKUs ranked by total sales volume and unit price
                    </CardDescription>
                  </div>
                  <Badge variant="outline" className="text-xs">
                    Top {dashboardData.top_products.length} Items
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border bg-secondary/30 text-muted-foreground text-left">
                        <th className="p-3 font-semibold">Rank</th>
                        <th className="p-3 font-semibold">Product ID / SKU</th>
                        <th className="p-3 font-semibold">Revenue Generated</th>
                        <th className="p-3 font-semibold">Units Sold</th>
                        <th className="p-3 font-semibold">Average Unit Price</th>
                        <th className="p-3 font-semibold">Revenue Share</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/50">
                      {dashboardData.top_products.map((p, idx) => (
                        <tr key={p.product_id} className="hover:bg-secondary/20 transition-colors">
                          <td className="p-3 font-mono font-bold text-muted-foreground">#{idx + 1}</td>
                          <td className="p-3 font-mono font-medium text-foreground">{p.product_id}</td>
                          <td className="p-3 font-mono font-bold text-emerald-400">
                            ${p.revenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                          <td className="p-3 text-foreground">{p.units_sold.toLocaleString()} units</td>
                          <td className="p-3 font-mono text-muted-foreground">${p.avg_price.toFixed(2)}</td>
                          <td className="p-3">
                            <div className="flex items-center gap-2">
                              <div className="w-16 h-1.5 rounded-full bg-secondary overflow-hidden">
                                <div
                                  className="h-full bg-primary rounded-full"
                                  style={{ width: `${Math.min(100, p.percentage_of_total * 4)}%` }}
                                />
                              </div>
                              <span className="font-mono text-[11px] text-muted-foreground">
                                {p.percentage_of_total}%
                              </span>
                            </div>
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
      ) : null}
    </div>
  );
}
