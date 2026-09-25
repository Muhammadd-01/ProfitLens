import { useState, useEffect } from 'react';
import {
  FileText,
  Download,
  Sparkles,
  RefreshCw,
  Plus,
  Calendar,
  CheckCircle2,
  AlertTriangle,
  Database,
  ChevronDown,
  ChevronUp,
  BookOpen,
  FileCheck,
  FileType,
  Table,
  Sliders,
  DollarSign,
  ShieldAlert,
  Users,
  Package,
  MessageSquareQuote,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/common/empty-state';
import { useDatasetStore } from '@/stores/dataset-store';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import type {
  ReportMetadataItem,
  ReportListResponse,
  ReportGenerateRequest,
  Dataset,
} from '@/types';

export function ReportsPage() {
  const { datasets, activeDataset, setActiveDataset, setDatasets } = useDatasetStore();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [reports, setReports] = useState<ReportMetadataItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Modal / Generator Config
  const [showConfig, setShowConfig] = useState(false);
  const [reportType, setReportType] = useState<ReportGenerateRequest['report_type']>('executive_summary');
  const [reportFormat, setReportFormat] = useState<'pdf' | 'csv'>('pdf');
  const [customTitle, setCustomTitle] = useState('');
  const [includeChurn, setIncludeChurn] = useState(true);
  const [includeAnomalies, setIncludeAnomalies] = useState(true);
  const [includeProducts, setIncludeProducts] = useState(true);
  const [includeSentiment, setIncludeSentiment] = useState(true);

  // Pedagogy
  const [showPedagogy, setShowPedagogy] = useState(false);

  useEffect(() => {
    if (datasets.length === 0) {
      loadDatasets();
    } else if (activeDataset?.id) {
      loadReports(activeDataset.id);
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
        loadReports(first.id);
      } else {
        setLoading(false);
      }
    } catch {
      setLoading(false);
    }
  };

  const loadReports = async (datasetId: string) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get<ReportListResponse>(`/reports/${datasetId}/list`);
      setReports(resp.data.reports);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Unable to load generated reports.';
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
      const payload: ReportGenerateRequest = {
        report_type: reportType,
        format: reportFormat,
        title: customTitle.trim() || undefined,
        include_churn: includeChurn,
        include_anomalies: includeAnomalies,
        include_products: includeProducts,
        include_sentiment: includeSentiment,
      };

      const resp = await api.post<ReportMetadataItem>(`/reports/${activeDataset.id}/generate`, payload);
      setReports([resp.data, ...reports]);
      setShowConfig(false);
      setCustomTitle('');
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Report compilation failed.';
      setError(msg);
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = (report: ReportMetadataItem) => {
    if (!activeDataset?.id) return;
    // Download directly via window navigation or anchor
    const downloadUrl = `/api/reports/${activeDataset.id}/download/${report.id}`;
    window.open(downloadUrl, '_blank');
  };

  const formatFileSize = (bytes: number) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  if (!activeDataset && !loading) {
    return (
      <EmptyState
        icon={Database}
        title="No Datasets Available"
        description="Upload or connect a transaction dataset to generate board-ready PDF and CSV reports."
        actionLabel="Go to Datasets"
        onAction={() => navigate('/dashboard/datasets')}
      />
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header & Actions */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <FileText className="w-6 h-6 text-primary" />
              Multi-Format Corporate Report Generator
            </h1>
            <Badge variant="outline" className="text-xs font-mono">
              Phase 17 Active
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Compile publication-ready executive PDF deliverables and financial CSV audit exports powered by ReportLab layout engines.
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
                  loadReports(found.id);
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
            onClick={() => setShowConfig(!showConfig)}
            className="flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Compile New Deliverable
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-500 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <Button variant="ghost" size="sm" onClick={() => loadReports(activeDataset!.id)}>
            Retry
          </Button>
        </div>
      )}

      {/* Generator Configuration Drawer / Card */}
      {showConfig && (
        <Card className="border-primary/30 bg-card shadow-md animate-in fade-in-50 duration-200">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <Sliders className="w-4 h-4 text-primary" />
              Configure Corporate Deliverable
            </CardTitle>
            <CardDescription className="text-xs">
              Select deliverable scope, document format, and analytical module inclusions.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Report Type */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">Report Focus</label>
                <select
                  className="w-full bg-card border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  value={reportType}
                  onChange={(e) => setReportType(e.target.value as ReportGenerateRequest['report_type'])}
                >
                  <option value="executive_summary">Executive Summary Audit (All Modules)</option>
                  <option value="financial_audit">Financial & Revenue Trajectory Audit</option>
                  <option value="risk_assessment">Customer Churn & Anomaly Risk Assessment</option>
                  <option value="catalog_intelligence">Product Catalog & BCG Matrix Intelligence</option>
                </select>
              </div>

              {/* Format Toggle */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">Output Format</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setReportFormat('pdf')}
                    className={`flex items-center justify-center gap-2 py-2 px-3 rounded-lg border text-sm font-medium transition-all ${
                      reportFormat === 'pdf'
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border bg-card text-muted-foreground hover:bg-muted'
                    }`}
                  >
                    <FileType className="w-4 h-4 text-red-500" />
                    PDF Document (.pdf)
                  </button>
                  <button
                    type="button"
                    onClick={() => setReportFormat('csv')}
                    className={`flex items-center justify-center gap-2 py-2 px-3 rounded-lg border text-sm font-medium transition-all ${
                      reportFormat === 'csv'
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border bg-card text-muted-foreground hover:bg-muted'
                    }`}
                  >
                    <Table className="w-4 h-4 text-emerald-500" />
                    CSV Data Export (.csv)
                  </button>
                </div>
              </div>
            </div>

            {/* Custom Title */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">
                Document Title Override <span className="text-muted-foreground font-normal">(Optional)</span>
              </label>
              <input
                type="text"
                placeholder="e.g. Q1 2026 Executive Financial & Risk Audit"
                className="w-full bg-card border rounded-lg px-3 py-2 text-sm placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary"
                value={customTitle}
                onChange={(e) => setCustomTitle(e.target.value)}
              />
            </div>

            {/* Section Checkboxes */}
            {reportFormat === 'pdf' && (
              <div className="space-y-2 pt-2 border-t">
                <span className="text-xs font-semibold text-foreground">Included Analytical Sections</span>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <label className="flex items-center gap-2 text-xs font-medium cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeChurn}
                      onChange={(e) => setIncludeChurn(e.target.checked)}
                      className="rounded border-border text-primary focus:ring-primary"
                    />
                    <Users className="w-3.5 h-3.5 text-purple-500" /> Customer Churn
                  </label>
                  <label className="flex items-center gap-2 text-xs font-medium cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeAnomalies}
                      onChange={(e) => setIncludeAnomalies(e.target.checked)}
                      className="rounded border-border text-primary focus:ring-primary"
                    />
                    <ShieldAlert className="w-3.5 h-3.5 text-red-500" /> Anomaly & Fraud Logs
                  </label>
                  <label className="flex items-center gap-2 text-xs font-medium cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeProducts}
                      onChange={(e) => setIncludeProducts(e.target.checked)}
                      className="rounded border-border text-primary focus:ring-primary"
                    />
                    <Package className="w-3.5 h-3.5 text-blue-500" /> Product BCG Matrix
                  </label>
                  <label className="flex items-center gap-2 text-xs font-medium cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeSentiment}
                      onChange={(e) => setIncludeSentiment(e.target.checked)}
                      className="rounded border-border text-primary focus:ring-primary"
                    />
                    <MessageSquareQuote className="w-3.5 h-3.5 text-pink-500" /> Customer Sentiment
                  </label>
                </div>
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-3 border-t">
              <Button variant="ghost" size="sm" onClick={() => setShowConfig(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleGenerate}
                disabled={generating}
                className="flex items-center gap-2"
              >
                {generating ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4 text-amber-300" />
                )}
                {generating ? 'Compiling Deliverable...' : 'Generate & Download'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Reports History Table */}
      <Card className="border-border/50 bg-card">
        <CardHeader className="pb-3 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <FileCheck className="w-5 h-5 text-emerald-500" />
              Compiled Deliverables History
            </CardTitle>
            <CardDescription className="text-xs">
              Audit-ready deliverables generated for dataset {activeDataset?.name || ''}.
            </CardDescription>
          </div>
          <Badge variant="secondary" className="text-xs">
            {reports.length} Deliverables Compiled
          </Badge>
        </CardHeader>

        <CardContent className="p-0">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16">
              <RefreshCw className="w-7 h-7 animate-spin text-primary mb-2" />
              <p className="text-xs text-muted-foreground">Loading report archive...</p>
            </div>
          ) : reports.length === 0 ? (
            <div className="p-10 text-center">
              <FileText className="w-10 h-10 text-muted-foreground mx-auto mb-2 opacity-40" />
              <h3 className="text-sm font-medium text-foreground">No Deliverables Compiled Yet</h3>
              <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                Generate an Executive Summary PDF or CSV financial export to share board-ready intelligence with stakeholders.
              </p>
              <Button
                size="sm"
                onClick={() => setShowConfig(true)}
                className="mt-4 text-xs"
              >
                Compile Your First Report
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b bg-muted/40 text-muted-foreground font-semibold">
                    <th className="py-2.5 px-4 text-left">Deliverable Title</th>
                    <th className="py-2.5 px-4 text-left">Format</th>
                    <th className="py-2.5 px-4 text-left">Report Type</th>
                    <th className="py-2.5 px-4 text-left">Compiled Date</th>
                    <th className="py-2.5 px-4 text-left">Size</th>
                    <th className="py-2.5 px-4 text-left">Key Highlights</th>
                    <th className="py-2.5 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {reports.map((report) => {
                    const isPdf = report.format === 'pdf';
                    const kpis = report.summary_kpis || {};

                    return (
                      <tr key={report.id} className="hover:bg-muted/30 transition-colors">
                        <td className="py-3 px-4 font-medium text-foreground">
                          <div className="flex items-center gap-2">
                            {isPdf ? (
                              <FileType className="w-4 h-4 text-red-500 shrink-0" />
                            ) : (
                              <Table className="w-4 h-4 text-emerald-500 shrink-0" />
                            )}
                            <span>{report.report_name}</span>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <Badge
                            variant="outline"
                            className={`text-2xs uppercase ${
                              isPdf
                                ? 'bg-red-500/10 text-red-500 border-red-500/30'
                                : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/30'
                            }`}
                          >
                            {report.format}
                          </Badge>
                        </td>
                        <td className="py-3 px-4 capitalize text-muted-foreground">
                          {report.report_type.replace(/_/g, ' ')}
                        </td>
                        <td className="py-3 px-4 text-muted-foreground">
                          {report.created_at.slice(0, 10)} {report.created_at.slice(11, 16)}
                        </td>
                        <td className="py-3 px-4 font-mono text-muted-foreground">
                          {formatFileSize(report.file_size_bytes)}
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex flex-wrap items-center gap-1.5">
                            {kpis.total_revenue && (
                              <span className="bg-muted px-1.5 py-0.5 rounded text-2xs font-mono text-foreground">
                                Rev: ${Number(kpis.total_revenue).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                              </span>
                            )}
                            {kpis.revenue_at_risk && (
                              <span className="bg-red-500/10 text-red-500 px-1.5 py-0.5 rounded text-2xs font-mono">
                                At Risk: ${Number(kpis.revenue_at_risk).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                              </span>
                            )}
                            {kpis.net_sentiment_score && (
                              <span className="bg-emerald-500/10 text-emerald-500 px-1.5 py-0.5 rounded text-2xs font-mono">
                                NSS: {Number(kpis.net_sentiment_score).toFixed(1)}%
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleDownload(report)}
                            className="text-xs flex items-center gap-1 ml-auto"
                          >
                            <Download className="w-3.5 h-3.5" />
                            Download
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

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
                Section 38 Masterclass: Multi-Format Document Compilation & Automated Reporting
              </CardTitle>
            </div>
            {showPedagogy ? (
              <ChevronUp className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            )}
          </div>
          <CardDescription className="text-xs">
            Architectural principles of high-fidelity corporate PDF generation, flowable pagination, and financial data serialization.
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
                Decision makers, board members, auditors, and external investors require self-contained, audit-ready deliverables. While interactive dashboards are valuable for day-to-day operators, executive governance relies on formal point-in-time documentation for quarterly reviews, loan compliance covenants, and risk oversight. Manual report compilation costs business analysts 8 to 15 hours per week cutting and pasting charts into spreadsheets and slide decks, introducing version drift and human calculation errors.
              </p>
            </div>

            {/* 2. Data Science & Engineering Problem */}
            <div className="space-y-1.5">
              <h4 className="font-bold text-primary flex items-center gap-2 text-sm">
                2. Data Science & Engineering Problem
              </h4>
              <p>
                Compiling multi-page corporate PDFs server-side presents intricate engineering challenges:
              </p>
              <ul className="list-disc pl-5 space-y-1 text-xs text-muted-foreground">
                <li>Flowable pagination: Dynamically breaking tables and paragraphs across page boundaries without clipping or orphan headers.</li>
                <li>Dynamic total page calculation: Standard single-pass PDF rendering cannot compute "Page X of Y" because the denominator is unknown until document completion.</li>
                <li>Zero-leak streaming: Compiling documents in memory via byte streams without writing unbounded temporary files or exhausting memory under concurrent requests.</li>
              </ul>
            </div>

            {/* 3. Relevant Concept */}
            <div className="space-y-1.5">
              <h4 className="font-bold text-primary flex items-center gap-2 text-sm">
                3. Relevant Concept: Document Flowables & Two-Pass Canvas Architecture
              </h4>
              <p>
                ReportLab uses a flow-based document model (Platypus). Content elements (Paragraphs, Tables, Spacers, KeepTogether) are "Flowables" that are poured into a template container. To solve the total page count problem, ProfitLens implements a custom <code>NumberedCanvas</code> subclass. During document building, the canvas intercepts <code>showPage()</code> and caches page state dicts. Upon <code>save()</code>, it computes the final page count {'$N$'} and executes a second rendering pass to stamp running headers and "Page {'$p$'} of {'$N$'}" footers.
              </p>
            </div>

            {/* 4. Mathematics */}
            <div className="space-y-1.5">
              <h4 className="font-bold text-primary flex items-center gap-2 text-sm">
                4. Mathematical Foundation: Flowable Box Model Geometry
              </h4>
              <p>
                Table layout geometry enforces proportional width allocation across print margins:
              </p>
              <div className="p-3 bg-card border rounded-md font-mono text-xs overflow-x-auto my-2 text-center">
                {'W_{\\text{available}} = W_{\\text{page}} - (M_{\\text{left}} + M_{\\text{right}})'}
              </div>
              <p className="text-xs text-muted-foreground">
                Where standard letter size has {'$W_{\\text{page}} = 612\\,\\text{pt}$'}, margins {'$M_{\\text{left}} = M_{\\text{right}} = 36\\,\\text{pt}$'}, yielding an available width of {'$540\\,\\text{pt}$'}. Individual column widths {'$w_j$'} satisfy {'$\\sum_{j=1}^m w_j = W_{\\text{available}}$'}.
              </p>
            </div>

            {/* 5. Algorithm */}
            <div className="space-y-1.5">
              <h4 className="font-bold text-primary flex items-center gap-2 text-sm">
                5. The Algorithm: Multi-Section Flowable Pipeline
              </h4>
              <ol className="list-decimal pl-5 space-y-1 text-xs text-muted-foreground">
                <li><strong>Harvester</strong>: Queries dataset transactions and inspects downstream metadata (Churn risk tiers, Isolation Forest anomalies, BCG product quadrants, and ABSA sentiment).</li>
                <li><strong>Story Composition</strong>: Assembles Cover Banner, Executive KPI Scorecard, Monthly Revenue Table, Churn Matrix, BCG Distribution, Anomaly Triage Log, and Prescriptive Recommendations.</li>
                <li><strong>NumberedCanvas Two-Pass Render</strong>: Measures layout constraints, manages page breaks, and stamps corporate confidentiality headers and page numbers.</li>
                <li><strong>Persistence & Streaming</strong>: Writes output to <code>data/reports/{'{dataset_id}'}_{'{report_id}'}.pdf</code>, registers metadata, and streams file via <code>FileResponse</code>.</li>
              </ol>
            </div>

            {/* 6. Code Architecture */}
            <div className="space-y-1.5">
              <h4 className="font-bold text-primary flex items-center gap-2 text-sm">
                6. Code Architecture
              </h4>
              <p className="text-xs text-muted-foreground">
                Backend services reside in <code>app/services/report_service.py</code> with endpoints in <code>app/api/reports.py</code> (<code>GET /list</code>, <code>POST /generate</code>, <code>GET /download</code>). The frontend page resides in <code>frontend/src/pages/reports/reports-page.tsx</code>.
              </p>
            </div>

            {/* 7. Output Interpretation */}
            <div className="space-y-1.5">
              <h4 className="font-bold text-primary flex items-center gap-2 text-sm">
                7. Output Interpretation
              </h4>
              <p className="text-xs text-muted-foreground">
                The generated deliverable provides an end-to-end management narrative: Executive Scorecard highlights immediate baseline health, risk chapters quantify capital at risk ($), product breakdowns identify catalog dependencies, and the prescriptive playbook delivers tactical action items.
              </p>
            </div>

            {/* 8. Limitations & Edge Cases */}
            <div className="space-y-1.5">
              <h4 className="font-bold text-primary flex items-center gap-2 text-sm">
                8. Limitations
              </h4>
              <p className="text-xs text-muted-foreground">
                Point-in-time PDF documents do not reflect subsequent transaction arrivals without recompilation. Extreme text length in review snippets or reasons requires strict wrapping or truncation to prevent page overflow.
              </p>
            </div>
          </CardContent>
        )}
      </Card>
    </div>
  );
}
