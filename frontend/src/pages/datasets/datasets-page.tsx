import { useState, useEffect } from 'react';
import {
  Database,
  Plus,
  FileSpreadsheet,
  Calendar,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
  GitMerge,
  Sparkles,
  Layers,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/common/empty-state';
import { TableSkeleton } from '@/components/common/loading-skeleton';
import { FileDropzone } from '@/components/upload/file-dropzone';
import { DataQualityCard } from '@/components/profiling/data-quality-card';
import { ColumnProfileTable } from '@/components/profiling/column-profile-table';
import { ColumnMappingDialog } from '@/components/mapping/column-mapping-dialog';
import { DataCleaningCard } from '@/components/cleaning/data-cleaning-card';
import { FeatureCatalogCard } from '@/components/features/feature-catalog-card';
import { useDatasetStore } from '@/stores/dataset-store';
import api from '@/lib/api';
import type { Dataset, DatasetUploadResponse, DataQualityReport, SchemaValidationResult } from '@/types';
import { useNavigate } from 'react-router-dom';

export function DatasetsPage() {
  const [showUpload, setShowUpload] = useState(false);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'profiling' | 'mapping' | 'cleaning' | 'features'>('profiling');
  const [profilingLoading, setProfilingLoading] = useState(false);
  const [qualityReport, setQualityReport] = useState<DataQualityReport | null>(null);

  const { datasets, setDatasets, activeDataset, setActiveDataset, addDataset } = useDatasetStore();
  const navigate = useNavigate();

  useEffect(() => {
    fetchDatasets();
  }, []);

  useEffect(() => {
    if (activeDataset?.id) {
      loadProfilingReport(activeDataset.id);
    }
  }, [activeDataset?.id]);

  const fetchDatasets = async () => {
    setLoading(true);
    try {
      const response = await api.get<{ datasets: Dataset[]; total: number }>('/datasets');
      setDatasets(response.data.datasets);
      if (!activeDataset && response.data.datasets.length > 0) {
        setActiveDataset(response.data.datasets[0]);
      }
    } catch {
      // Offline fallback
    } finally {
      setLoading(false);
    }
  };

  const loadProfilingReport = async (datasetId: string) => {
    setProfilingLoading(true);
    try {
      const response = await api.get<DataQualityReport>(`/datasets/${datasetId}/profile`);
      setQualityReport(response.data);
    } catch {
      setQualityReport(null);
    } finally {
      setProfilingLoading(false);
    }
  };

  const handleRunProfiling = async (datasetId: string) => {
    setProfilingLoading(true);
    try {
      const response = await api.post<DataQualityReport>(`/datasets/${datasetId}/profile`);
      setQualityReport(response.data);
    } catch {
      // Handled
    } finally {
      setProfilingLoading(false);
    }
  };

  const handleUploadSuccess = (uploaded: DatasetUploadResponse) => {
    const newDataset: Dataset = {
      id: uploaded.id,
      name: uploaded.name,
      file_type: uploaded.file_type,
      file_size_bytes: uploaded.file_size_bytes,
      row_count: uploaded.row_count,
      column_count: uploaded.column_count,
      data_quality_score: null,
      column_mappings: null,
      column_metadata: { columns: [] },
      profiling_results: null,
      status: 'uploaded',
      created_at: uploaded.created_at,
    };
    addDataset(newDataset);
    setActiveDataset(newDataset);
    loadProfilingReport(uploaded.id);
    setActiveTab('profiling');
  };

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return '—';
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-8 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Datasets & Schema Alignment</h1>
          <p className="text-muted-foreground text-sm">
            Upload business records, review data quality diagnostics, and align columns with ProfitLens models
          </p>
        </div>
        <Button
          onClick={() => setShowUpload(!showUpload)}
          className="flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          {showUpload ? 'Close Upload' : 'Upload Dataset'}
        </Button>
      </div>

      {showUpload && (
        <Card className="border-border bg-card">
          <CardHeader>
            <CardTitle className="text-lg">Upload Business Dataset</CardTitle>
            <CardDescription>
              We stream in chunks to preserve RAM, sniff encodings, detect delimiters, and extract schema
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FileDropzone onUploadSuccess={handleUploadSuccess} />
          </CardContent>
        </Card>
      )}

      {loading ? (
        <TableSkeleton rows={4} />
      ) : datasets.length === 0 && !showUpload ? (
        <EmptyState
          icon={Database}
          title="No datasets uploaded yet"
          description="Upload your first CSV or Excel file to discover revenue trends, customer churn risks, and predictive forecasts."
          actionLabel="Upload Your Business Data"
          onAction={() => setShowUpload(true)}
        />
      ) : (
        <div className="space-y-6">
          {/* Datasets List */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-muted-foreground uppercase font-semibold px-4">
              <span>Dataset</span>
              <div className="flex gap-14 mr-4">
                <span>Records</span>
                <span>Size</span>
                <span>Uploaded</span>
                <span>Action</span>
              </div>
            </div>

            <div className="space-y-2">
              {datasets.map((d) => {
                const isActive = activeDataset?.id === d.id;
                return (
                  <Card
                    key={d.id}
                    className={`border-border bg-card transition-colors hover:border-primary/40 ${
                      isActive ? 'border-primary/50 bg-secondary/20' : ''
                    }`}
                  >
                    <CardContent className="flex items-center justify-between p-4">
                      <div className="flex items-center gap-3">
                        <div className="rounded-lg bg-primary/10 p-2 text-primary">
                          <FileSpreadsheet className="h-5 w-5" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-foreground text-sm">{d.name}</span>
                            {isActive && (
                              <Badge variant="default" className="text-[10px] h-4 bg-primary/20 text-primary border-primary/30">
                                Active
                              </Badge>
                            )}
                          </div>
                          <span className="text-xs text-muted-foreground uppercase">{d.file_type}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-10 text-sm text-foreground">
                        <span className="w-16 text-right font-medium">
                          {d.row_count ? d.row_count.toLocaleString() : '—'}
                        </span>
                        <span className="w-16 text-right text-muted-foreground">
                          {formatFileSize(d.file_size_bytes)}
                        </span>
                        <div className="flex items-center gap-1 text-xs text-muted-foreground w-28 justify-end">
                          <Calendar className="h-3.5 w-3.5" />
                          <span>{formatDate(d.created_at)}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setActiveDataset(d);
                              loadProfilingReport(d.id);
                            }}
                            className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
                          >
                            <ShieldCheck className="h-3.5 w-3.5" />
                            Inspect
                          </Button>
                          {isActive && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => navigate('/dashboard')}
                              className="text-xs flex items-center gap-1"
                            >
                              Explore <ArrowRight className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>

          {/* Active Dataset Inspection & Alignment Hub */}
          {activeDataset && (
            <div className="space-y-6 pt-4 border-t border-border">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
                    <span>{activeDataset.name}</span>
                    <Badge variant="secondary" className="text-xs font-normal capitalize">
                      {activeDataset.status}
                    </Badge>
                  </h2>
                  <p className="text-xs text-muted-foreground">
                    Inspect diagnosed data health or review and customize column mappings
                  </p>
                </div>

                {/* Sub-Navigation Tabs */}
                <div className="flex items-center rounded-lg bg-secondary/60 p-1 border border-border">
                  <button
                    onClick={() => setActiveTab('profiling')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                      activeTab === 'profiling'
                        ? 'bg-card text-foreground shadow-sm'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                    Data Health & Profiling
                  </button>
                  <button
                    onClick={() => setActiveTab('mapping')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                      activeTab === 'mapping'
                        ? 'bg-card text-foreground shadow-sm'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    <GitMerge className="h-3.5 w-3.5 text-primary" />
                    Column Mapping & Readiness
                  </button>
                  <button
                    onClick={() => setActiveTab('cleaning')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                      activeTab === 'cleaning'
                        ? 'bg-card text-foreground shadow-sm'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    <Sparkles className="h-3.5 w-3.5 text-primary" />
                    Clean & Standardize
                  </button>
                  <button
                    onClick={() => setActiveTab('features')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                      activeTab === 'features'
                        ? 'bg-card text-foreground shadow-sm'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    <Layers className="h-3.5 w-3.5 text-primary" />
                    Engineered Features
                  </button>
                </div>
              </div>

              {/* Tab 1: Data Health & Profiling */}
              {activeTab === 'profiling' && (
                <div className="space-y-6">
                  <div className="flex justify-end">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleRunProfiling(activeDataset.id)}
                      disabled={profilingLoading}
                      className="text-xs flex items-center gap-1.5"
                    >
                      <RefreshCw className={`h-3.5 w-3.5 ${profilingLoading ? 'animate-spin' : ''}`} />
                      {profilingLoading ? 'Analyzing...' : 'Re-run Profiling'}
                    </Button>
                  </div>

                  {profilingLoading ? (
                    <TableSkeleton rows={6} />
                  ) : qualityReport ? (
                    <div className="space-y-6">
                      <DataQualityCard report={qualityReport} />
                      <ColumnProfileTable columns={qualityReport.columns} />
                    </div>
                  ) : (
                    <Card className="border-border bg-card p-6 text-center">
                      <p className="text-sm text-muted-foreground mb-4">
                        This dataset has not been profiled yet. Click below to inspect column distributions and calculate its Data Quality Score.
                      </p>
                      <Button
                        size="sm"
                        onClick={() => handleRunProfiling(activeDataset.id)}
                        className="flex items-center gap-2 mx-auto"
                      >
                        <ShieldCheck className="h-4 w-4" /> Run Quality Profiling
                      </Button>
                    </Card>
                  )}
                </div>
              )}

              {/* Tab 2: Column Mapping & Readiness */}
              {activeTab === 'mapping' && (
                <div className="space-y-6">
                  <ColumnMappingDialog
                    datasetId={activeDataset.id}
                    datasetName={activeDataset.name}
                    onSaved={() => {
                      // Refresh dataset metadata
                      fetchDatasets();
                    }}
                    onProceedToCleaning={() => setActiveTab('cleaning')}
                  />
                </div>
              )}

              {/* Tab 3: Data Cleaning & Transformation */}
              {activeTab === 'cleaning' && (
                <div className="space-y-6">
                  <DataCleaningCard
                    datasetId={activeDataset.id}
                    datasetName={activeDataset.name}
                    onCleaned={() => {
                      fetchDatasets();
                    }}
                    onProceedToFeatures={() => setActiveTab('features')}
                  />
                </div>
              )}

              {/* Tab 4: Feature Engineering */}
              {activeTab === 'features' && (
                <div className="space-y-6">
                  <FeatureCatalogCard
                    datasetId={activeDataset.id}
                    datasetName={activeDataset.name}
                    onProceedToAnalytics={() => navigate('/dashboard')}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
