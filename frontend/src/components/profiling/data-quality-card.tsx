import { ShieldCheck, AlertTriangle, AlertCircle, Info, CheckCircle2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import type { DataQualityReport } from '@/types';
import { cn } from '@/lib/utils';

interface DataQualityCardProps {
  report: DataQualityReport;
}

export function DataQualityCard({ report }: DataQualityCardProps) {
  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-emerald-400';
    if (score >= 80) return 'text-blue-400';
    if (score >= 65) return 'text-amber-400';
    return 'text-rose-400';
  };

  const getBadgeVariant = (grade: string) => {
    if (grade === 'Excellent') return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    if (grade === 'Good') return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    if (grade === 'Fair') return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
  };

  const criticalIssuesCount = report.issues.filter((i) => i.severity === 'critical').length;
  const warningIssuesCount = report.issues.filter((i) => i.severity === 'warning').length;

  return (
    <Card className="border-border bg-card">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="rounded-lg bg-primary/10 p-2 text-primary">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-base font-semibold">Data Quality Health</CardTitle>
              <CardDescription className="text-xs">
                Automated statistical profiling and integrity assessment
              </CardDescription>
            </div>
          </div>
          <Badge variant="outline" className={cn('text-xs font-semibold px-2.5 py-0.5', getBadgeVariant(report.quality_grade))}>
            {report.quality_grade} Quality ({report.quality_score}%)
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Score & Visual Gauge */}
        <div className="space-y-2">
          <div className="flex items-baseline justify-between">
            <span className="text-sm font-medium text-muted-foreground">Overall Health Score</span>
            <span className={cn('text-3xl font-bold tracking-tight', getScoreColor(report.quality_score))}>
              {report.quality_score}%
            </span>
          </div>
          <Progress value={report.quality_score} className="h-2.5 bg-secondary" />
        </div>

        {/* Metric Breakdown Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-lg bg-secondary/40 p-3">
            <span className="text-xs text-muted-foreground font-medium">Missing Cells</span>
            <p className="text-lg font-bold text-foreground mt-0.5">
              {report.total_missing_percentage}%
            </p>
            <span className="text-[11px] text-muted-foreground">
              {report.total_missing_cells.toLocaleString()} cells
            </span>
          </div>

          <div className="rounded-lg bg-secondary/40 p-3">
            <span className="text-xs text-muted-foreground font-medium">Duplicate Rows</span>
            <p className="text-lg font-bold text-foreground mt-0.5">
              {report.duplicate_rows_percentage}%
            </p>
            <span className="text-[11px] text-muted-foreground">
              {report.duplicate_rows_count.toLocaleString()} rows
            </span>
          </div>

          <div className="rounded-lg bg-secondary/40 p-3">
            <span className="text-xs text-muted-foreground font-medium">Detected Roles</span>
            <p className="text-lg font-bold text-foreground mt-0.5">
              {Object.keys(report.detected_roles).length}
            </p>
            <span className="text-[11px] text-muted-foreground">Core business entities</span>
          </div>

          <div className="rounded-lg bg-secondary/40 p-3">
            <span className="text-xs text-muted-foreground font-medium">Issues Found</span>
            <p className="text-lg font-bold text-foreground mt-0.5">
              {report.issues.length}
            </p>
            <span className="text-[11px] text-muted-foreground">
              {criticalIssuesCount} critical, {warningIssuesCount} warnings
            </span>
          </div>
        </div>

        {/* Human Language Explanations */}
        {report.issues.length > 0 && (
          <div className="space-y-3 pt-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Diagnosed Data Issues & Business Impact
            </h4>
            <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
              {report.issues.map((issue, idx) => (
                <div
                  key={idx}
                  className={cn(
                    'rounded-lg border p-3.5 space-y-1 text-sm transition-colors',
                    issue.severity === 'critical'
                      ? 'border-destructive/30 bg-destructive/5 text-destructive-foreground'
                      : issue.severity === 'warning'
                      ? 'border-amber-500/30 bg-amber-500/5 text-foreground'
                      : 'border-border bg-secondary/20 text-foreground'
                  )}
                >
                  <div className="flex items-start gap-2.5">
                    {issue.severity === 'critical' ? (
                      <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                    ) : issue.severity === 'warning' ? (
                      <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                    ) : (
                      <Info className="h-4 w-4 text-blue-400 shrink-0 mt-0.5" />
                    )}
                    <div className="space-y-1">
                      <p className="font-medium text-xs text-foreground">
                        {issue.column ? `Column [${issue.column}]: ` : ''}
                        {issue.description}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        <span className="font-medium text-foreground/80">Recommendation:</span> {issue.recommendation}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
