import { useState, useEffect } from 'react';
import {
  MessageSquareQuote,
  Sparkles,
  RefreshCw,
  Search,
  ThumbsUp,
  ThumbsDown,
  Minus,
  Star,
  Tag,
  Box,
  Truck,
  Headphones,
  DollarSign,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Database,
  Sliders,
  Filter,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/common/empty-state';
import { useDatasetStore } from '@/stores/dataset-store';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import type {
  SentimentOverviewResponse,
  SentimentReviewItem,
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
  PieChart,
  Pie,
} from 'recharts';

export function SentimentPage() {
  const { datasets, activeDataset, setActiveDataset, setDatasets } = useDatasetStore();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [data, setData] = useState<SentimentOverviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [sentimentFilter, setSentimentFilter] = useState<string>('all');
  const [aspectFilter, setAspectFilter] = useState<string>('all');
  const [showPedagogy, setShowPedagogy] = useState(false);

  useEffect(() => {
    if (datasets.length === 0) {
      loadDatasets();
    } else if (activeDataset?.id) {
      loadSentimentOverview(activeDataset.id);
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
        loadSentimentOverview(first.id);
      } else {
        setLoading(false);
      }
    } catch {
      setLoading(false);
    }
  };

  const loadSentimentOverview = async (datasetId: string) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get<SentimentOverviewResponse>(
        `/ml/${datasetId}/sentiment/overview`
      );
      setData(resp.data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Unable to load customer review sentiment analysis.';
      setError(msg);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeSentiment = async () => {
    if (!activeDataset) return;
    setAnalyzing(true);
    setError(null);
    try {
      const resp = await api.post<SentimentOverviewResponse>(
        `/ml/${activeDataset.id}/sentiment/analyze`
      );
      setData(resp.data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Customer sentiment analysis execution failed.';
      setError(msg);
    } finally {
      setAnalyzing(false);
    }
  };

  // Filter reviews
  const filteredReviews = (data?.recent_reviews || []).filter((r) => {
    if (sentimentFilter !== 'all' && r.sentiment_label !== sentimentFilter) return false;
    if (aspectFilter !== 'all' && !r.aspect_tags.includes(aspectFilter)) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchText = r.review_text.toLowerCase().includes(q);
      const matchCust = (r.customer_id || '').toLowerCase().includes(q);
      const matchProd = (r.product_id || '').toLowerCase().includes(q);
      return matchText || matchCust || matchProd;
    }
    return true;
  });

  const getAspectIcon = (aspect: string) => {
    switch (aspect) {
      case 'Product Quality':
        return <Box className="w-4 h-4 text-emerald-500" />;
      case 'Shipping & Delivery':
        return <Truck className="w-4 h-4 text-blue-500" />;
      case 'Customer Service':
        return <Headphones className="w-4 h-4 text-purple-500" />;
      case 'Pricing & Value':
        return <DollarSign className="w-4 h-4 text-amber-500" />;
      default:
        return <Tag className="w-4 h-4 text-slate-500" />;
    }
  };

  const getSentimentBadge = (label: string) => {
    switch (label) {
      case 'positive':
        return (
          <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 gap-1 text-[11px]">
            <ThumbsUp className="w-3 h-3" /> Positive
          </Badge>
        );
      case 'negative':
        return (
          <Badge className="bg-rose-500/10 text-rose-600 border-rose-500/20 gap-1 text-[11px]">
            <ThumbsDown className="w-3 h-3" /> Negative
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" className="bg-slate-500/10 text-slate-600 border-slate-500/20 gap-1 text-[11px]">
            <Minus className="w-3 h-3" /> Neutral
          </Badge>
        );
    }
  };

  // Pie chart data
  const pieData = data
    ? [
        { name: 'Positive', value: data.distribution.positive_count, color: '#10b981' },
        { name: 'Neutral', value: data.distribution.neutral_count, color: '#64748b' },
        { name: 'Negative', value: data.distribution.negative_count, color: '#f43f5e' },
      ]
    : [];

  // Aspect bar data
  const aspectBarData = (data?.aspects || []).map((a) => ({
    name: a.aspect,
    score: a.avg_sentiment_score,
    mentions: a.total_mentions,
    positive: a.positive_mentions,
    negative: a.negative_mentions,
  }));

  if (datasets.length === 0 && !loading) {
    return (
      <div className="p-8">
        <EmptyState
          icon={MessageSquareQuote}
          title="No Datasets Uploaded"
          description="Upload an e-commerce dataset containing customer feedback or reviews to analyze natural language sentiment."
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
              <MessageSquareQuote className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Customer Review & Sentiment Intelligence</h1>
              <p className="text-sm text-muted-foreground">
                Natural Language Processing (NLP) polarity scoring, Aspect-Based Sentiment Analysis (ABSA), and TF-IDF extraction.
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
                  loadSentimentOverview(ds.id);
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
            onClick={handleAnalyzeSentiment}
            disabled={analyzing || loading || !activeDataset}
            className="gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${analyzing ? 'animate-spin' : ''}`} />
            {analyzing ? 'Analyzing...' : 'Run NLP Scan'}
          </Button>

          <Button
            variant="outline"
            onClick={() => setShowPedagogy(!showPedagogy)}
            className="gap-2 text-xs"
          >
            <HelpCircle className="w-4 h-4 text-blue-500" />
            NLP Masterclass
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
              Educational Masterclass: Natural Language Sentiment & Aspect-Based NLP (ABSA)
            </div>
            <CardDescription className="text-xs sm:text-sm">
              Mathematical foundations of commercial sentiment polarity, VADER hyperbolic scaling, and TF-IDF salience.
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
                  Numeric star ratings (1 to 5) fail to explain <em>why</em> customers churn. A 2-star rating could stem from a
                  defective product, a delivery delay, or an unhelpful customer support agent. Merchandisers require automated
                  qualitative diagnostics to isolate root causes without reading thousands of comments manually.
                </p>
              </div>

              <div className="p-4 rounded-lg bg-card border space-y-2">
                <h4 className="font-semibold text-foreground flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-500" />
                  2. The Data Science Problem
                </h4>
                <p className="text-muted-foreground text-xs leading-relaxed">
                  Customer feedback text is high-dimensional, unstructured, and noisy. We apply rule-based valence intensity
                  scoring with negation flipping ("not good"), intensifier multipliers ("extremely fast"), and domain-specific
                  aspect dictionaries to classify sentiment across distinct operational pillars.
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
                  <p className="font-mono font-semibold text-primary">Compound Valence Normalization:</p>
                  <p className="text-muted-foreground">
                    Word valence scores are summed and mapped to [-1.0, 1.0] via hyperbolic normalization:
                  </p>
                  <div className="font-mono bg-background p-2 rounded border text-center text-xs space-y-1">
                    <div>{`Compound = raw_sum / sqrt(raw_sum^2 + alpha)`}</div>
                    <div className="text-[11px] text-muted-foreground">{`where alpha = 15.0 and raw_sum = Sum(v_i)`}</div>
                  </div>
                  <p className="text-muted-foreground">
                    Reviews with Compound &ge; +0.05 are Positive, &le; -0.05 are Negative, otherwise Neutral.
                  </p>
                </div>

                <div className="space-y-2 bg-muted/40 p-3 rounded-md">
                  <p className="font-mono font-semibold text-primary">Term Frequency-Inverse Document Frequency (TF-IDF):</p>
                  <p className="text-muted-foreground">
                    Measures keyword importance relative to the entire customer review corpus:
                  </p>
                  <div className="font-mono bg-background p-2 rounded border text-center text-xs">
                    {`TF-IDF(t, d) = TF(t, d) * [ln((1 + |D|) / (1 + |{d in D : t in d}|)) + 1]`}
                  </div>
                  <p className="text-muted-foreground">
                    Suppresses pervasive stop-words while surfacing distinctive terms driving positive or negative customer experiences.
                  </p>
                </div>
              </div>
            </div>

            {/* Net Sentiment Score */}
            <div className="p-4 rounded-lg bg-card border space-y-2">
              <h4 className="font-semibold text-foreground flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                4. Net Sentiment Score (NSS) Executive KPI
              </h4>
              <p className="text-muted-foreground text-xs leading-relaxed">
                Modeled after the Net Promoter Score (NPS): <code className="font-mono font-bold">NSS = (% Positive - % Negative) &times; 100</code>.
                Ranging from -100 to +100, an NSS above +50 indicates brand advocacy, while an NSS below 0 reveals systemic
                product or delivery failure requiring executive escalation.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading state */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center space-y-4">
          <RefreshCw className="w-8 h-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Tokenizing reviews, calculating valence compound scores, and grouping aspect pillars...</p>
        </div>
      ) : data ? (
        <>
          {/* Executive KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="border-border">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground">Net Sentiment Score</span>
                  <div className={`p-2 rounded-lg ${data.distribution.net_sentiment_score >= 0 ? 'bg-emerald-500/10 text-emerald-600' : 'bg-rose-500/10 text-rose-600'}`}>
                    {data.distribution.net_sentiment_score >= 0 ? <ThumbsUp className="w-4 h-4" /> : <ThumbsDown className="w-4 h-4" />}
                  </div>
                </div>
                <div className="mt-3">
                  <div className={`text-2xl font-bold tracking-tight ${data.distribution.net_sentiment_score >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {data.distribution.net_sentiment_score >= 0 ? `+${data.distribution.net_sentiment_score.toFixed(1)}%` : `${data.distribution.net_sentiment_score.toFixed(1)}%`}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    % Positive ({((data.distribution.positive_count / Math.max(1, data.distribution.total_reviews)) * 100).toFixed(0)}%) minus % Negative ({((data.distribution.negative_count / Math.max(1, data.distribution.total_reviews)) * 100).toFixed(0)}%)
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground">Reviews Analyzed</span>
                  <div className="p-2 rounded-lg bg-primary/10 text-primary">
                    <MessageSquareQuote className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-2xl font-bold tracking-tight">
                    {data.distribution.total_reviews.toLocaleString()}
                  </div>
                  <div className="flex items-center gap-1.5 mt-1 text-xs text-muted-foreground">
                    {data.distribution.avg_rating && (
                      <span className="flex items-center text-amber-500 font-medium">
                        <Star className="w-3.5 h-3.5 fill-amber-500 mr-1" />
                        {data.distribution.avg_rating.toFixed(1)} / 5.0
                      </span>
                    )}
                    <span>Avg compound: {data.distribution.avg_compound_score.toFixed(2)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-emerald-500/20 bg-emerald-500/5">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-emerald-600">Positive Reviews</span>
                  <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-600">
                    <ThumbsUp className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-2xl font-bold tracking-tight text-emerald-600">
                    {data.distribution.positive_count.toLocaleString()}{' '}
                    <span className="text-xs font-normal text-muted-foreground">
                      ({((data.distribution.positive_count / Math.max(1, data.distribution.total_reviews)) * 100).toFixed(1)}%)
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Customers delighted with quality, value, or fulfillment
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-rose-500/20 bg-rose-500/5">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-rose-600">Negative Feedback</span>
                  <div className="p-2 rounded-lg bg-rose-500/10 text-rose-600">
                    <ThumbsDown className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-2xl font-bold tracking-tight text-rose-600">
                    {data.distribution.negative_count.toLocaleString()}{' '}
                    <span className="text-xs font-normal text-muted-foreground">
                      ({((data.distribution.negative_count / Math.max(1, data.distribution.total_reviews)) * 100).toFixed(1)}%)
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Complaints flagged for customer support / QA review
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Aspect-Based Pillars & Donut Chart Row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Sentiment Proportion Donut */}
            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold">Sentiment Balance</CardTitle>
                <CardDescription className="text-xs">
                  Proportional split across positive, neutral, and negative customer comments.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[220px] w-full flex items-center justify-center">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={80}
                        paddingAngle={4}
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const p = payload[0].payload;
                            return (
                              <div className="p-2.5 bg-card border rounded-lg shadow-xl text-xs">
                                <p className="font-semibold text-foreground">{p.name}</p>
                                <p className="text-muted-foreground">{p.value} reviews ({((p.value / Math.max(1, data.distribution.total_reviews)) * 100).toFixed(1)}%)</p>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex items-center justify-center gap-4 text-xs mt-2 border-t pt-3">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Positive ({data.distribution.positive_count})
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-slate-500" /> Neutral ({data.distribution.neutral_count})
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Negative ({data.distribution.negative_count})
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Aspect Polarity Bar Chart */}
            <Card className="border-border lg:col-span-2">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold">Aspect-Based Sentiment Index</CardTitle>
                <CardDescription className="text-xs">
                  Average polarity score across core business operations. Positive (&gt; 0) vs Negative (&lt; 0).
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[220px] w-full pt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={aspectBarData} margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis domain={[-0.8, 0.8]} tick={{ fontSize: 11 }} tickFormatter={(v) => v.toFixed(1)} />
                      <Tooltip
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const p = payload[0].payload;
                            return (
                              <div className="p-3 bg-card border rounded-lg shadow-xl text-xs space-y-1">
                                <p className="font-semibold text-foreground">{p.name}</p>
                                <p className="font-mono text-primary">Avg Score: {p.score >= 0 ? `+${p.score.toFixed(2)}` : p.score.toFixed(2)}</p>
                                <p className="text-muted-foreground">{p.mentions} total mentions ({p.positive} positive, {p.negative} negative)</p>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                        {aspectBarData.map((entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={entry.score >= 0 ? '#10b981' : '#f43f5e'}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* High-Salience TF-IDF Keywords */}
          {data.top_keywords.length > 0 && (
            <Card className="border-border">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary" />
                  Corpus Keyword Drivers (TF-IDF Salience)
                </CardTitle>
                <CardDescription className="text-xs">
                  Statistically significant phrases extracted from reviews, color-coded by customer sentiment bias.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {data.top_keywords.map((kw, i) => (
                    <div
                      key={i}
                      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                        kw.sentiment === 'positive'
                          ? 'bg-emerald-500/10 text-emerald-700 border-emerald-500/20'
                          : kw.sentiment === 'negative'
                          ? 'bg-rose-500/10 text-rose-700 border-rose-500/20'
                          : 'bg-slate-500/10 text-slate-700 border-slate-500/20'
                      }`}
                    >
                      <span>{kw.keyword}</span>
                      <span className="text-[10px] opacity-70">({kw.frequency})</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Customer Reviews Feed Table */}
          <Card className="border-border">
            <CardHeader className="pb-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <CardTitle className="text-base font-semibold flex items-center gap-2">
                    <MessageSquareQuote className="w-4 h-4 text-primary" />
                    Customer Feedback Stream
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Individual reviews scored with polarity compound scores and classified operational aspect tags.
                  </CardDescription>
                </div>

                {/* Filters */}
                <div className="flex flex-wrap items-center gap-2.5">
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted-foreground" />
                    <input
                      type="text"
                      placeholder="Search text, customer, SKU..."
                      className="pl-8 pr-3 py-1.5 text-xs bg-muted/50 border rounded-lg focus:outline-none focus:ring-1 focus:ring-primary w-48"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>

                  <select
                    className="text-xs bg-muted/50 border rounded-lg px-2.5 py-1.5 focus:outline-none cursor-pointer"
                    value={sentimentFilter}
                    onChange={(e) => setSentimentFilter(e.target.value)}
                  >
                    <option value="all">All Sentiments</option>
                    <option value="positive">Positive</option>
                    <option value="neutral">Neutral</option>
                    <option value="negative">Negative</option>
                  </select>

                  <select
                    className="text-xs bg-muted/50 border rounded-lg px-2.5 py-1.5 focus:outline-none cursor-pointer"
                    value={aspectFilter}
                    onChange={(e) => setAspectFilter(e.target.value)}
                  >
                    <option value="all">All Aspects</option>
                    <option value="Product Quality">Product Quality</option>
                    <option value="Shipping & Delivery">Shipping & Delivery</option>
                    <option value="Customer Service">Customer Service</option>
                    <option value="Pricing & Value">Pricing & Value</option>
                  </select>
                </div>
              </div>
            </CardHeader>

            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-muted/50 border-y text-muted-foreground uppercase tracking-wider text-[10px]">
                    <tr>
                      <th className="py-3 px-4">Rating & Date</th>
                      <th className="py-3 px-4">Customer & SKU</th>
                      <th className="py-3 px-4">Review Text</th>
                      <th className="py-3 px-4">Aspect Tags</th>
                      <th className="py-3 px-4">Compound Score</th>
                      <th className="py-3 px-4 text-right">Sentiment</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {filteredReviews.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="text-center py-8 text-muted-foreground">
                          No reviews match the selected filters.
                        </td>
                      </tr>
                    ) : (
                      filteredReviews.map((r) => (
                        <tr key={r.id} className="hover:bg-muted/30 transition-colors">
                          <td className="py-3 px-4 whitespace-nowrap">
                            <div className="flex items-center gap-1 font-semibold text-foreground">
                              {r.rating !== null && r.rating !== undefined ? (
                                <>
                                  <Star className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />
                                  <span>{r.rating}</span>
                                </>
                              ) : (
                                <span className="text-muted-foreground">N/A</span>
                              )}
                            </div>
                            <div className="text-[11px] text-muted-foreground">{r.order_date || 'Recent'}</div>
                          </td>
                          <td className="py-3 px-4 whitespace-nowrap">
                            <div className="font-mono text-foreground">{r.customer_id || 'Guest'}</div>
                            <div className="text-[11px] text-muted-foreground font-mono">{r.product_id || 'General'}</div>
                          </td>
                          <td className="py-3 px-4 max-w-md">
                            <p className="text-xs text-foreground leading-relaxed italic">
                              "{r.review_text}"
                            </p>
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex flex-wrap gap-1">
                              {r.aspect_tags.map((asp, idx) => (
                                <Badge key={idx} variant="outline" className="text-[10px] py-0 px-1.5 flex items-center gap-1 bg-muted/30">
                                  {getAspectIcon(asp)}
                                  <span>{asp}</span>
                                </Badge>
                              ))}
                            </div>
                          </td>
                          <td className="py-3 px-4 whitespace-nowrap font-mono font-medium">
                            <span className={r.sentiment_score >= 0.05 ? 'text-emerald-600' : r.sentiment_score <= -0.05 ? 'text-rose-600' : 'text-slate-600'}>
                              {r.sentiment_score >= 0 ? `+${r.sentiment_score.toFixed(2)}` : r.sentiment_score.toFixed(2)}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-right whitespace-nowrap">
                            {getSentimentBadge(r.sentiment_label)}
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
