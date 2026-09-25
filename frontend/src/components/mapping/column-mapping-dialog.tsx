import { useState, useEffect } from 'react';
import {
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Sparkles,
  Layers,
  Save,
  Loader2,
  Check,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';
import type {
  ColumnMappingResponse,
  ColumnMappingSuggestion,
  SchemaValidationResult,
} from '@/types';
import { cn } from '@/lib/utils';

interface ColumnMappingDialogProps {
  datasetId: string;
  datasetName: string;
  onSaved?: (validation: SchemaValidationResult) => void;
  onProceedToCleaning?: () => void;
}

export function ColumnMappingDialog({
  datasetId,
  datasetName,
  onSaved,
  onProceedToCleaning,
}: ColumnMappingDialogProps) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [suggestions, setSuggestions] = useState<ColumnMappingSuggestion[]>([]);
  const [availableColumns, setAvailableColumns] = useState<string[]>([]);
  const [selectedMappings, setSelectedMappings] = useState<Record<string, string>>({});
  const [validationResult, setValidationResult] = useState<SchemaValidationResult | null>(null);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    fetchMappingSuggestions();
  }, [datasetId]);

  const fetchMappingSuggestions = async () => {
    setLoading(true);
    try {
      const response = await api.get<ColumnMappingResponse>(`/datasets/${datasetId}/mappings`);
      setSuggestions(response.data.mappings);
      setAvailableColumns(response.data.available_columns);

      // Pre-fill state with suggested mappings
      const initial: Record<string, string> = {};
      response.data.mappings.forEach((m) => {
        if (m.mapped_column) {
          initial[m.canonical_field] = m.mapped_column;
        }
      });
      setSelectedMappings(initial);

      // Initial validation
      validateCurrent(initial);
    } catch {
      // Handled
    } finally {
      setLoading(false);
    }
  };

  const validateCurrent = async (mappings: Record<string, string>) => {
    try {
      const response = await api.post<SchemaValidationResult>(`/datasets/${datasetId}/mappings`, {
        mappings,
      });
      setValidationResult(response.data);
    } catch {
      // Ignore during live typing/selection
    }
  };

  const handleSelectChange = (canonicalField: string, columnValue: string) => {
    const updated = { ...selectedMappings };
    if (columnValue === '__none__') {
      delete updated[canonicalField];
    } else {
      updated[canonicalField] = columnValue;
    }
    setSelectedMappings(updated);
    setSavedSuccess(false);
    validateCurrent(updated);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await api.post<SchemaValidationResult>(`/datasets/${datasetId}/mappings`, {
        mappings: selectedMappings,
      });
      setValidationResult(response.data);
      setSavedSuccess(true);
      if (onSaved) {
        onSaved(response.data);
      }
    } catch {
      // Error handling
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Card className="border-border bg-card p-10 flex flex-col items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary mb-3" />
        <p className="text-sm text-muted-foreground">Analyzing schema and computing fuzzy token similarities...</p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="border-border bg-card">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="rounded-lg bg-primary/10 p-2 text-primary">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-base font-semibold">Smart Column Alignment</CardTitle>
                <CardDescription className="text-xs">
                  Match your file columns to standard ProfitLens business concepts
                </CardDescription>
              </div>
            </div>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1.5"
            >
              {saving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : savedSuccess ? (
                <Check className="h-4 w-4 text-emerald-400" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              {savedSuccess ? 'Mappings Saved!' : 'Confirm Mappings'}
            </Button>
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Mapping Grid */}
          <div className="space-y-3">
            <div className="grid grid-cols-12 text-xs font-semibold text-muted-foreground uppercase px-3 py-1">
              <span className="col-span-5">Business Concept</span>
              <span className="col-span-3 text-center">Confidence</span>
              <span className="col-span-4">Matched File Column</span>
            </div>

            <div className="space-y-2">
              {suggestions.map((s) => {
                const currentMapped = selectedMappings[s.canonical_field] || '__none__';
                return (
                  <div
                    key={s.canonical_field}
                    className="grid grid-cols-12 items-center rounded-lg border border-border bg-secondary/20 p-3 hover:bg-secondary/35 transition-colors gap-2"
                  >
                    {/* Concept Name & Info */}
                    <div className="col-span-5 space-y-0.5">
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-sm text-foreground">
                          {s.field_display_name}
                        </span>
                        {s.is_required ? (
                          <Badge variant="destructive" className="text-[10px] h-4 px-1.5 font-normal">
                            Required
                          </Badge>
                        ) : (
                          <span className="text-[10px] text-muted-foreground">Optional</span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-1">{s.description}</p>
                    </div>

                    {/* Confidence Match Badge */}
                    <div className="col-span-3 flex justify-center">
                      {s.confidence_level === 'high' ? (
                        <Badge variant="outline" className="text-[11px] bg-emerald-500/10 text-emerald-400 border-emerald-500/20 gap-1">
                          <CheckCircle2 className="h-3 w-3" /> Auto-matched ({(s.confidence * 100).toFixed(0)}%)
                        </Badge>
                      ) : s.confidence_level === 'medium' ? (
                        <Badge variant="outline" className="text-[11px] bg-amber-500/10 text-amber-400 border-amber-500/20 gap-1">
                          <Sparkles className="h-3 w-3" /> Suggested ({(s.confidence * 100).toFixed(0)}%)
                        </Badge>
                      ) : (
                        <Badge variant="secondary" className="text-[11px] text-muted-foreground">
                          Unmapped
                        </Badge>
                      )}
                    </div>

                    {/* Dropdown Selector */}
                    <div className="col-span-4">
                      <select
                        value={currentMapped}
                        onChange={(e) => handleSelectChange(s.canonical_field, e.target.value)}
                        className="w-full rounded-md border border-border bg-card px-3 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none"
                      >
                        <option value="__none__">— Not Mapped / None —</option>
                        {availableColumns.map((col) => (
                          <option key={col} value={col}>
                            {col}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Module Readiness Validation Gatekeeper */}
          {validationResult && (
            <div className="rounded-xl border border-border bg-secondary/30 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Layers className="h-4 w-4 text-primary" />
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground">
                    Downstream Analytics & ML Readiness
                  </h4>
                </div>
                <span className="text-xs text-muted-foreground font-medium">
                  {validationResult.summary_message}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                {validationResult.module_readiness.map((m) => (
                  <div
                    key={m.module}
                    className={cn(
                      'rounded-lg border p-2.5 text-xs space-y-1',
                      m.is_ready
                        ? 'border-emerald-500/20 bg-emerald-500/5'
                        : 'border-border bg-card/60 opacity-80'
                    )}
                  >
                    <div className="flex items-center justify-between font-medium">
                      <span>{m.module}</span>
                      {m.is_ready ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                      ) : (
                        <AlertCircle className="h-3.5 w-3.5 text-muted-foreground" />
                      )}
                    </div>
                    <p className="text-[11px] text-muted-foreground line-clamp-1">{m.message}</p>
                  </div>
                ))}
              </div>

              {onProceedToCleaning && (
                <div className="flex justify-end pt-2 border-t border-border/50">
                  <Button
                    size="sm"
                    onClick={onProceedToCleaning}
                    className="text-xs flex items-center gap-1.5 bg-primary text-primary-foreground"
                  >
                    Continue to Data Cleaning <ArrowRight className="h-3.5 w-3.5" />
                  </Button>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
