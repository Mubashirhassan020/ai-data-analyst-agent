import { AlertCircle, AlertTriangle, Info } from "lucide-react";
import type { DatasetProfile, Issue } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { cn } from "@/lib/utils";

const METRICS: { key: keyof DatasetProfile["quality"]; label: string }[] = [
  { key: "completeness", label: "Completeness" },
  { key: "missing_values", label: "Missing Values" },
  { key: "duplicates", label: "Duplicates" },
  { key: "data_types", label: "Data Types" },
  { key: "outliers", label: "Outliers" },
];

function scoreColor(score10: number): string {
  if (score10 >= 8) return "bg-emerald-500";
  if (score10 >= 5) return "bg-amber-500";
  return "bg-red-500";
}

function overallColor(score100: number): string {
  if (score100 >= 80) return "text-emerald-400";
  if (score100 >= 50) return "text-amber-400";
  return "text-red-400";
}

const severityIcon: Record<Issue["severity"], React.ElementType> = {
  info: Info,
  low: Info,
  medium: AlertTriangle,
  high: AlertCircle,
};

const severityTone: Record<Issue["severity"], string> = {
  info: "text-sky-400",
  low: "text-muted",
  medium: "text-amber-400",
  high: "text-red-400",
};

export function QualityScoreCard({ profile }: { profile: DatasetProfile }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Data Quality Score</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-baseline gap-2">
            <span className={cn("text-4xl font-bold tabular-nums", overallColor(profile.quality.overall))}>
              {profile.quality.overall}
            </span>
            <span className="text-muted text-sm">/ 100</span>
          </div>
          <div className="space-y-2.5">
            {METRICS.map(({ key, label }) => {
              const score = profile.quality[key] as number;
              return (
                <div key={key}>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-muted">{label}</span>
                    <span className="font-medium tabular-nums">{score.toFixed(1)}/10</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-border/60 overflow-hidden">
                    <div
                      className={cn("h-full rounded-full", scoreColor(score))}
                      style={{ width: `${(score / 10) * 100}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Detected Issues ({profile.issues.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {profile.issues.length === 0 ? (
            <p className="text-xs text-muted">No issues detected — this dataset looks clean.</p>
          ) : (
            <ul className="space-y-2.5 max-h-80 overflow-y-auto">
              {profile.issues.map((issue, i) => {
                const Icon = severityIcon[issue.severity];
                return (
                  <li key={i} className="flex items-start gap-2 text-xs">
                    <Icon className={cn("h-3.5 w-3.5 mt-0.5 shrink-0", severityTone[issue.severity])} />
                    <span className="text-fg/90">{issue.message}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
