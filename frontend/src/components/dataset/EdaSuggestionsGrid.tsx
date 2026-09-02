import { useEdaSuggestions } from "@/hooks/useDatasets";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { Card, CardContent } from "@/components/ui/Card";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/States";
import { Sparkles } from "lucide-react";

export function EdaSuggestionsGrid({ datasetId }: { datasetId: string }) {
  const { data, isLoading, isError, refetch } = useEdaSuggestions(datasetId);

  if (isLoading) return <LoadingState label="Generating suggested visualizations…" />;
  if (isError) return <ErrorState description="Could not generate suggestions." onRetry={() => refetch()} />;
  if (!data || data.charts.length === 0) {
    return (
      <EmptyState
        icon={<Sparkles className="h-6 w-6" />}
        title="No automatic suggestions"
        description="This dataset's columns don't have an obvious chart-worthy pattern yet. Try the Analysis Builder below."
      />
    );
  }

  return (
    <div className="grid md:grid-cols-2 gap-4">
      {data.charts.map((chart, i) => (
        <Card key={i}>
          <CardContent className="pt-4">
            <PlotlyChart data={chart.data} layout={chart.layout} height={260} />
            <p className="text-xs text-muted mt-2 pt-2 border-t border-border/60">{chart.reason}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
