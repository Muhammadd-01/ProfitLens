import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import type { ColumnProfile } from '@/types';
import { cn } from '@/lib/utils';
import { Tag, Hash, Calendar, Binary, Key, AlignLeft } from 'lucide-react';

interface ColumnProfileTableProps {
  columns: ColumnProfile[];
}

export function ColumnProfileTable({ columns }: ColumnProfileTableProps) {
  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'numeric':
        return <Hash className="h-3.5 w-3.5" />;
      case 'datetime':
        return <Calendar className="h-3.5 w-3.5" />;
      case 'boolean':
        return <Binary className="h-3.5 w-3.5" />;
      case 'identifier':
        return <Key className="h-3.5 w-3.5" />;
      case 'categorical':
        return <Tag className="h-3.5 w-3.5" />;
      default:
        return <AlignLeft className="h-3.5 w-3.5" />;
    }
  };

  const getTypeBadgeClass = (type: string) => {
    switch (type) {
      case 'numeric':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'datetime':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      case 'boolean':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'identifier':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'categorical':
        return 'bg-pink-500/10 text-pink-400 border-pink-500/20';
      default:
        return 'bg-secondary text-muted-foreground';
    }
  };

  return (
    <Card className="border-border bg-card">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">Column Profiling & Type Inference</CardTitle>
        <CardDescription className="text-xs">
          Automatic semantic type inference, missing value percentages, and unique value counts
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-border text-muted-foreground uppercase font-semibold">
                <th className="pb-3 pl-2">Column</th>
                <th className="pb-3">Inferred Type</th>
                <th className="pb-3">Detected Role</th>
                <th className="pb-3">Missingness</th>
                <th className="pb-3">Unique Values</th>
                <th className="pb-3">Sample Values</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {columns.map((col) => (
                <tr key={col.name} className="hover:bg-secondary/20 transition-colors">
                  <td className="py-3 pl-2 font-mono font-medium text-foreground">
                    {col.name}
                  </td>
                  <td className="py-3">
                    <Badge variant="outline" className={cn('text-[11px] font-normal gap-1 capitalize', getTypeBadgeClass(col.inferred_type))}>
                      {getTypeIcon(col.inferred_type)}
                      {col.inferred_type}
                    </Badge>
                  </td>
                  <td className="py-3">
                    {col.potential_role ? (
                      <Badge variant="secondary" className="text-[10px] bg-primary/10 text-primary border-primary/20 capitalize font-medium">
                        ✓ {col.potential_role.replace('_', ' ')}
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground/60">—</span>
                    )}
                  </td>
                  <td className="py-3 min-w-[130px]">
                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px]">
                        <span className={col.missing_percentage > 0 ? 'text-amber-400 font-medium' : 'text-muted-foreground'}>
                          {col.missing_percentage}%
                        </span>
                        <span className="text-muted-foreground text-[10px]">
                          ({col.missing_count})
                        </span>
                      </div>
                      <Progress
                        value={col.missing_percentage}
                        className={cn('h-1.5', col.missing_percentage > 5 ? 'bg-amber-500/20 [&>div]:bg-amber-400' : 'bg-secondary')}
                      />
                    </div>
                  </td>
                  <td className="py-3 font-mono text-muted-foreground">
                    {col.unique_count.toLocaleString()}
                    <span className="text-[10px] text-muted-foreground/70 ml-1">
                      ({(col.uniqueness_ratio * 100).toFixed(1)}%)
                    </span>
                  </td>
                  <td className="py-3 max-w-xs">
                    <div className="flex flex-wrap gap-1">
                      {col.sample_values.slice(0, 3).map((val, idx) => (
                        <span
                          key={idx}
                          className="rounded bg-secondary/60 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground truncate max-w-[120px]"
                        >
                          {val}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
