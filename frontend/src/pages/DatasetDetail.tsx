import { useParams } from "react-router-dom";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/Tabs";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadingState, ErrorState } from "@/components/ui/States";
import { useDataset, useDatasetColumns, useDatasetProfile } from "@/hooks/useDatasets";
import { DataPreviewTable } from "@/components/dataset/DataPreviewTable";
import { QualityScoreCard } from "@/components/dataset/QualityScoreCard";
import { ColumnsTable } from "@/components/dataset/ColumnsTable";
import { EdaSuggestionsGrid } from "@/components/dataset/EdaSuggestionsGrid";
import { ChartBuilder } from "@/components/dataset/ChartBuilder";
import { AIChatPanel } from "@/components/chat/AIChatPanel";
import { formatBytes, formatDate, formatNumber } from "@/lib/format";

const statusTone = { ready: "success", processing: "warning", uploaded: "info", failed: "danger" } as const;

export default function DatasetDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: dataset, isLoading, isError, refetch } = useDataset(id);

  if (isLoading) return <LoadingState label="Loading dataset…" />;
  if (isError || !dataset) return <ErrorState description="Could not load this dataset." onRetry={() => refetch()} />;

  if (dataset.status === "failed") {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <ErrorState title="Dataset processing failed" description={dataset.error_message ?? undefined} />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">{dataset.original_filename}</h2>
            <Badge tone={statusTone[dataset.status]}>{dataset.status}</Badge>
          </div>
          <p className="text-xs text-muted mt-1">
            {formatNumber(dataset.row_count)} rows · {formatNumber(dataset.column_count)} columns ·{" "}
            {formatBytes(dataset.file_size_bytes)} · uploaded {formatDate(dataset.created_at)}
          </p>
        </div>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="preview">Data Preview</TabsTrigger>
          <TabsTrigger value="quality">Data Quality</TabsTrigger>
          <TabsTrigger value="columns">Columns</TabsTrigger>
          <TabsTrigger value="viz">Visualizations</TabsTrigger>
          <TabsTrigger value="ai">AI Analysis</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="pt-5">
          <OverviewTab datasetId={dataset.id} />
        </TabsContent>

        <TabsContent value="preview" className="pt-5">
          <DataPreviewTable datasetId={dataset.id} />
        </TabsContent>

        <TabsContent value="quality" className="pt-5">
          <QualityTab datasetId={dataset.id} />
        </TabsContent>

        <TabsContent value="columns" className="pt-5">
          <ColumnsTab datasetId={dataset.id} />
        </TabsContent>

        <TabsContent value="viz" className="pt-5 space-y-6">
          <EdaSuggestionsGrid datasetId={dataset.id} />
          <ChartBuilder datasetId={dataset.id} />
        </TabsContent>

        <TabsContent value="ai" className="pt-5">
          <AIChatPanel datasetId={dataset.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function OverviewTab({ datasetId }: { datasetId: string }) {
  const { data: profile, isLoading, isError, refetch } = useDatasetProfile(datasetId);

  if (isLoading) return <LoadingState label="Computing profile…" />;
  if (isError || !profile) return <ErrorState description="Could not load the profile." onRetry={() => refetch()} />;

  const stats = [
    { label: "Rows", value: formatNumber(profile.row_count) },
    { label: "Columns", value: formatNumber(profile.column_count) },
    { label: "Missing cells", value: `${formatNumber(profile.missing_cells)} (${profile.missing_percentage.toFixed(1)}%)` },
    { label: "Duplicate rows", value: formatNumber(profile.duplicate_rows) },
  ];

  return (
    <div className="space-y-6">
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s) => (
          <Card key={s.label}>
            <CardContent className="py-4">
              <p className="text-xs text-muted">{s.label}</p>
              <p className="text-lg font-semibold tabular-nums mt-1">{s.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      <QualityScoreCard profile={profile} />
    </div>
  );
}

function QualityTab({ datasetId }: { datasetId: string }) {
  const { data: profile, isLoading, isError, refetch } = useDatasetProfile(datasetId);
  if (isLoading) return <LoadingState label="Computing profile…" />;
  if (isError || !profile) return <ErrorState description="Could not load the profile." onRetry={() => refetch()} />;
  return <QualityScoreCard profile={profile} />;
}

function ColumnsTab({ datasetId }: { datasetId: string }) {
  const { data: columns, isLoading, isError, refetch } = useDatasetColumns(datasetId);
  if (isLoading) return <LoadingState label="Loading columns…" />;
  if (isError || !columns) return <ErrorState description="Could not load columns." onRetry={() => refetch()} />;
  return <ColumnsTable columns={columns} />;
}
