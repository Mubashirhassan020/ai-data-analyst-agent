import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { api } from "@/services/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { LoadingState, ErrorState } from "@/components/ui/States";

export default function Settings() {
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["health"], queryFn: api.health });

  return (
    <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>System Status</CardTitle>
          <CardDescription>Read-only — configured via the backend's environment variables.</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <LoadingState />
          ) : isError || !data ? (
            <ErrorState description="Could not reach the backend." onRetry={() => refetch()} />
          ) : (
            <dl className="grid sm:grid-cols-2 gap-4 text-sm">
              <Row label="Environment" value={data.environment} />
              <Row label="API version" value={data.version} />
              <Row label="Database" ok={data.db.ok} value={data.db.ok ? "Connected" : (data.db.detail ?? "Unavailable")} />
              <Row label="Storage backend" value={data.storage.backend} ok={data.storage.writable} />
              <Row
                label="AI provider"
                ok={data.llm_configured}
                value={data.llm_configured ? "Configured" : "Not configured — set LLM_API_KEY and LLM_MODEL"}
              />
            </dl>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>About</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted leading-relaxed space-y-2">
          <p>
            AI Data Analyst Agent grounds every AI answer in real tool calls against your uploaded data —
            Pandas aggregations, correlation, and outlier detection — never invented numbers.
          </p>
          <p>Upload limits, allowed file types, and the LLM provider are configured via the backend's <code>.env</code> file.</p>
        </CardContent>
      </Card>
    </div>
  );
}

function Row({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div>
      <dt className="text-xs text-muted mb-1">{label}</dt>
      <dd className="flex items-center gap-1.5 font-medium">
        {ok !== undefined &&
          (ok ? (
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
          ) : (
            <AlertTriangle className="h-3.5 w-3.5 text-amber-400 shrink-0" />
          ))}
        {value}
      </dd>
    </div>
  );
}
