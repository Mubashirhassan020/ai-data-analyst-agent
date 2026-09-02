import { Link } from "react-router-dom";
import { ArrowRight, Database, FileSpreadsheet, MessageSquare, Rows3 } from "lucide-react";
import { useDatasets } from "@/hooks/useDatasets";
import { UploadDropzone } from "@/components/upload/UploadDropzone";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/States";
import { formatBytes, formatDate, formatNumber } from "@/lib/format";

const statusTone = { ready: "success", processing: "warning", uploaded: "info", failed: "danger" } as const;

export default function Dashboard() {
  const { data: datasets, isLoading, isError, refetch } = useDatasets();

  const totalRows = datasets?.reduce((sum, d) => sum + (d.row_count ?? 0), 0) ?? 0;
  const readyCount = datasets?.filter((d) => d.status === "ready").length ?? 0;
  const latest = datasets?.[0];

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-8">
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard icon={Database} label="Total Datasets" value={formatNumber(datasets?.length ?? 0)} />
        <KpiCard icon={Rows3} label="Rows Analyzed" value={formatNumber(totalRows)} />
        <KpiCard icon={FileSpreadsheet} label="Ready Datasets" value={formatNumber(readyCount)} />
        <KpiCard icon={MessageSquare} label="Latest Dataset" value={latest?.original_filename ?? "—"} small />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Upload a new dataset</CardTitle>
        </CardHeader>
        <CardContent>
          <UploadDropzone />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Recent Datasets</CardTitle>
          <Link to="/app/datasets" className="text-xs text-accent hover:underline flex items-center gap-1">
            View all <ArrowRight className="h-3 w-3" />
          </Link>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <LoadingState />
          ) : isError ? (
            <ErrorState description="Could not load datasets." onRetry={() => refetch()} />
          ) : !datasets || datasets.length === 0 ? (
            <EmptyState
              icon={<Database className="h-6 w-6" />}
              title="No datasets yet"
              description="Upload a CSV or Excel file above to get started."
            />
          ) : (
            <ul className="divide-y divide-border/60">
              {datasets.slice(0, 5).map((d) => (
                <li key={d.id}>
                  <Link
                    to={`/app/datasets/${d.id}`}
                    className="flex items-center justify-between py-3 hover:bg-border/20 -mx-2 px-2 rounded-lg transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{d.original_filename}</p>
                      <p className="text-xs text-muted mt-0.5">
                        {formatNumber(d.row_count)} rows · {formatBytes(d.file_size_bytes)} · {formatDate(d.created_at)}
                      </p>
                    </div>
                    <Badge tone={statusTone[d.status]}>{d.status}</Badge>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function KpiCard({
  icon: Icon,
  label,
  value,
  small,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  small?: boolean;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 py-4">
        <div className="h-9 w-9 rounded-lg bg-accent/10 flex items-center justify-center text-accent shrink-0">
          <Icon className="h-4.5 w-4.5" />
        </div>
        <div className="min-w-0">
          <p className="text-xs text-muted">{label}</p>
          <p className={small ? "text-sm font-semibold truncate" : "text-lg font-semibold tabular-nums"}>{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}
