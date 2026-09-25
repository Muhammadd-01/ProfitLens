import { useState, useEffect } from 'react';
import {
  Sparkles,
  CheckCircle2,
  Trash2,
  Calendar,
  DollarSign,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  Sliders,
  Filter,
  Layers,
  FileCheck,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';
import type { CleaningSummary, CleaningStrategyConfig } from '@/types';
import { useNavigate } from 'react-router-dom';

interface DataCleaningCardProps {
  datasetId: string;
  datasetName: string;
  onCleaned?: (summary: CleaningSummary) => void;
  onProceedToFeatures?: () => void;
}

export function DataCleaningCard({ datasetId, datasetName, onCleaned, onProceedToFeatures }: DataCleaningCardProps) {
  const [cleaning, setCleaning] = useState(false);
  const [summary, setSummary] = useState<CleaningSummary | null>(null);
  const [loadingInitial, setLoadingInitial] = useState(true);
  const [showConfig, setShowConfig] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  // Cleaning strategy options
  const [config, setConfig] = useState<CleaningStrategyConfig>({
    handle_duplicates: true,
    impute_missing_numeric: 'median',
    impute_missing_categorical: 'mode',
    clip_outliers: true,
    clip_negative_values: true,
  });

  useEffect(() => {
    fetchExistingSummary();
  }, [datasetId]);

  const fetchExistingSummary = async () => {
    setLoadingInitial(true);
    setError(null);
    try {
      const response = await api.get<CleaningSummary>(`/datasets/${datasetId}/clean-summary`);
      setSummary(response.data);
    } catch {
      // Not yet cleaned
      setSummary(null);
    } finally {
      setLoadingInitial(false);
    }
  };

  const handleRunCleaning = async () => {
    setCleaning(true);
    setError(null);
    try {
      const response = await api.post<CleaningSummary>(`/datasets/${datasetId}/clean`, config);
      setSummary(response.data);
      if (onCleaned) {
        onCleaned(response.data);
      }
    } catch (err: unknown) {
      const errorMsg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Data cleaning execution failed. Please check column mappings.';
      setError(errorMsg);
    } finally {
      setCleaning(false);
    }
  };

  const getActionIcon = (actionType: string) => {
    switch (actionType) {
      case 'deduplication':
        return <Trash2 className="h-4 w-4 text-rose-400" />;
      case 'datetime_normalization':
        return <Calendar className="h-4 w-4 text-sky-400" />;
      case 'missing_imputation':
        return <Filter className="h-4 w-4 text-amber-400" />;
      case 'outlier_handling':
        return <Sliders className="h-4 w-4 text-purple-400" />;
      case 'type_coercion':
        return <DollarSign className="h-4 w-4 text-emerald-400" />;
      default:
        return <CheckCircle2 className="h-4 w-4 text-primary" />;
    }
  };

  const getActionBadgeClass = (actionType: string) => {
    switch (actionType) {
      case 'deduplication':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      case 'datetime_normalization':
        return 'bg-sky-500/10 text-sky-400 border-sky-500/20';
      case 'missing_imputation':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'outlier_handling':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      case 'type_coercion':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      default:
        return 'bg-primary/10 text-primary border-primary/20';
    }
  };

  return (
    <div className="space-y-6">
      {/* Control Banner */}
      <Card className="border-border bg-card">
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                Data Cleaning & Transformation Pipeline
              </CardTitle>
              <CardDescription>
                Automate deduplication, robust median imputation, negative price clipping, and datetime ISO-8601 UTC standardization
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowConfig(!showConfig)}
                className="text-xs flex items-center gap-1.5"
              >
                <Sliders className="h-3.5 w-3.5" />
                {showConfig ? 'Hide Config' : 'Cleaning Rules'}
              </Button>
              <Button
                size="sm"
                onClick={handleRunCleaning}
                disabled={cleaning}
                className="text-xs flex items-center gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${cleaning ? 'animate-spin' : ''}`} />
                {cleaning ? 'Standardizing...' : summary ? 'Re-run Pipeline' : 'Run Cleaning Pipeline'}
              </Button>
            </div>
          </div>
        </CardHeader>

        {/* Optional Configuration Panel */}
        {showConfig && (
          <CardContent className="border-t border-border pt-4 pb-4 bg-secondary/10">
            <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-3 tracking-wider">
              Pipeline Rule Parameters
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
              <label className="flex items-center gap-2 cursor-pointer p-2 rounded border border-border bg-card">
                <input
                  type="checkbox"
                  checked={config.handle_duplicates}
                  onChange={(e) => setConfig({ ...config, handle_duplicates: e.target.checked })}
                  className="rounded text-primary focus:ring-primary h-4 w-4 bg-secondary border-border"
                />
                <div>
                  <span className="font-medium text-foreground block">Deduplication</span>
                  <span className="text-muted-foreground text-[11px]">Drop exact duplicate rows & order keys</span>
                </div>
              </label>

              <div className="p-2 rounded border border-border bg-card">
                <span className="font-medium text-foreground block mb-1">Numeric Missing Imputation</span>
                <select
                  value={config.impute_missing_numeric}
                  onChange={(e) => setConfig({ ...config, impute_missing_numeric: e.target.value as any })}
                  className="w-full bg-secondary border border-border rounded px-2 py-1 text-xs text-foreground"
                >
                  <option value="median">Robust Median (Recommended for Skewed Sales)</option>
                  <option value="mean">Arithmetic Mean</option>
                  <option value="zero">Zero (0.0)</option>
                  <option value="drop">Drop Rows with Missing Numeric</option>
                </select>
              </div>

              <div className="p-2 rounded border border-border bg-card">
                <span className="font-medium text-foreground block mb-1">Categorical Imputation</span>
                <select
                  value={config.impute_missing_categorical}
                  onChange={(e) => setConfig({ ...config, impute_missing_categorical: e.target.value as any })}
                  className="w-full bg-secondary border border-border rounded px-2 py-1 text-xs text-foreground"
                >
                  <option value="mode">Most Frequent Mode (Recommended)</option>
                  <option value="unknown">Explicit "Unknown" Category</option>
                  <option value="drop">Drop Rows with Missing Categorical</option>
                </select>
              </div>

              <label className="flex items-center gap-2 cursor-pointer p-2 rounded border border-border bg-card">
                <input
                  type="checkbox"
                  checked={config.clip_negative_values}
                  onChange={(e) => setConfig({ ...config, clip_negative_values: e.target.checked })}
                  className="rounded text-primary focus:ring-primary h-4 w-4 bg-secondary border-border"
                />
                <div>
                  <span className="font-medium text-foreground block">Non-Negativity Guard</span>
                  <span className="text-muted-foreground text-[11px]">Clip negative revenues & quantities to 0.0</span>
                </div>
              </label>

              <label className="flex items-center gap-2 cursor-pointer p-2 rounded border border-border bg-card">
                <input
                  type="checkbox"
                  checked={config.clip_outliers}
                  onChange={(e) => setConfig({ ...config, clip_outliers: e.target.checked })}
                  className="rounded text-primary focus:ring-primary h-4 w-4 bg-secondary border-border"
                />
                <div>
                  <span className="font-medium text-foreground block">IQR Outlier Winsorization</span>
                  <span className="text-muted-foreground text-[11px]">Clip extreme values at 3.0× IQR fences</span>
                </div>
              </label>
            </div>
          </CardContent>
        )}

        {error && (
          <CardContent className="pt-0">
            <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          </CardContent>
        )}
      </Card>

      {/* Summary Metrics & Audit Trail */}
      {summary ? (
        <div className="space-y-6">
          {/* Status Metric Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="border-border bg-card">
              <CardContent className="p-4">
                <span className="text-xs text-muted-foreground block mb-1">Rows Processed</span>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-foreground">
                    {summary.cleaned_rows.toLocaleString()}
                  </span>
                  {summary.rows_removed > 0 && (
                    <span className="text-xs text-rose-400 font-medium">
                      -{summary.rows_removed.toLocaleString()} removed
                    </span>
                  )}
                </div>
                <span className="text-[11px] text-muted-foreground mt-1 block">
                  Original: {summary.original_rows.toLocaleString()} rows
                </span>
              </CardContent>
            </Card>

            <Card className="border-border bg-card">
              <CardContent className="p-4">
                <span className="text-xs text-muted-foreground block mb-1">Missing Cells Resolved</span>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-emerald-400">
                    {summary.original_missing_cells - summary.cleaned_missing_cells}
                  </span>
                  <span className="text-xs text-muted-foreground">cells</span>
                </div>
                <span className="text-[11px] text-muted-foreground mt-1 block">
                  Remaining unhandled: {summary.cleaned_missing_cells}
                </span>
              </CardContent>
            </Card>

            <Card className="border-border bg-card">
              <CardContent className="p-4">
                <span className="text-xs text-muted-foreground block mb-1">Transformation Steps</span>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-primary">
                    {summary.actions.length}
                  </span>
                  <span className="text-xs text-muted-foreground">audit logs</span>
                </div>
                <span className="text-[11px] text-muted-foreground mt-1 block">
                  Reproducible & deterministic
                </span>
              </CardContent>
            </Card>

            <Card className="border-border bg-card">
              <CardContent className="p-4">
                <span className="text-xs text-muted-foreground block mb-1">Dataset Status</span>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="default" className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 text-xs">
                    <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                    Ready for ML
                  </Badge>
                </div>
                <span className="text-[11px] text-muted-foreground mt-2 block truncate" title={summary.cleaned_file_path}>
                  Saved to Parquet/CSV cache
                </span>
              </CardContent>
            </Card>
          </div>

          {/* Audit Trail List */}
          <Card className="border-border bg-card">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base flex items-center gap-2">
                    <FileCheck className="h-4 w-4 text-primary" />
                    Transformation Audit Trail
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Step-by-step verification of data cleaning actions applied to {datasetName}
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  {onProceedToFeatures && (
                    <Button
                      size="sm"
                      onClick={onProceedToFeatures}
                      className="text-xs flex items-center gap-1.5 bg-primary text-primary-foreground"
                    >
                      Extract Features <ArrowRight className="h-3.5 w-3.5" />
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate('/dashboard')}
                    className="text-xs flex items-center gap-1.5"
                  >
                    Dashboard <ArrowRight className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {summary.actions.length === 0 ? (
                <div className="text-center py-6 text-muted-foreground text-xs">
                  Dataset was already clean. No transformation actions were needed.
                </div>
              ) : (
                <div className="space-y-2">
                  {summary.actions.map((action, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-3 rounded-lg border border-border bg-secondary/20 hover:bg-secondary/30 transition-colors text-xs"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-1.5 rounded-md bg-secondary border border-border">
                          {getActionIcon(action.action_type)}
                        </div>
                        <div>
                          <span className="font-medium text-foreground block">
                            {action.description}
                          </span>
                          {action.column && (
                            <span className="text-[11px] text-muted-foreground font-mono">
                              Column: {action.column}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant="outline"
                          className={`text-[10px] uppercase font-semibold tracking-wider ${getActionBadgeClass(action.action_type)}`}
                        >
                          {action.action_type.replace('_', ' ')}
                        </Badge>
                        <span className="text-xs font-semibold text-muted-foreground w-16 text-right">
                          {action.count_affected.toLocaleString()} affected
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card className="border-border bg-card p-8 text-center">
          <div className="max-w-md mx-auto space-y-3">
            <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <Sparkles className="h-6 w-6" />
            </div>
            <h3 className="text-base font-semibold text-foreground">Prepare Data for Predictive Modeling</h3>
            <p className="text-xs text-muted-foreground">
              Run our automated cleaning pipeline to standardize transaction dates, impute missing sales figures with robust medians, clip negative anomalies, and remove duplicate records.
            </p>
            <Button
              size="sm"
              onClick={handleRunCleaning}
              disabled={cleaning}
              className="mt-2 text-xs flex items-center gap-2 mx-auto bg-primary text-primary-foreground"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${cleaning ? 'animate-spin' : ''}`} />
              {cleaning ? 'Standardizing Dataset...' : 'Execute Data Cleaning Pipeline'}
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
