import { useState } from "react";
import { Wand2 } from "lucide-react";
import { useDatasetColumns } from "@/hooks/useDatasets";
import { useBuildChart } from "@/hooks/useAnalysis";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Select } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { LoadingState, ErrorState } from "@/components/ui/States";
import type { Aggregation, ChartType } from "@/types/api";

const CHART_TYPES: ChartType[] = ["bar", "grouped_bar", "line", "area", "scatter", "histogram", "box", "heatmap", "pie"];
const AGGREGATIONS: Aggregation[] = ["sum", "mean", "median", "count", "min", "max", "std"];

const NEEDS_X = new Set<ChartType>(["bar", "grouped_bar", "line", "area", "scatter", "box", "histogram"]);
const NEEDS_Y = new Set<ChartType>(["bar", "grouped_bar", "line", "area", "scatter", "box"]);
const NEEDS_GROUP = new Set<ChartType>(["grouped_bar", "line", "area", "scatter"]);
const IS_HEATMAP = new Set<ChartType>(["heatmap"]);

export function ChartBuilder({ datasetId }: { datasetId: string }) {
  const { data: columns, isLoading, isError, refetch } = useDatasetColumns(datasetId);
  const [chartType, setChartType] = useState<ChartType>("bar");
  const [x, setX] = useState("");
  const [y, setY] = useState("");
  const [aggregation, setAggregation] = useState<Aggregation>("sum");
  const [groupBy, setGroupBy] = useState("");
  const buildChart = useBuildChart();

  if (isLoading) return <LoadingState />;
  if (isError || !columns) return <ErrorState description="Could not load columns." onRetry={() => refetch()} />;

  const numericCols = columns.filter((c) => c.inferred_type === "integer" || c.inferred_type === "float");
  const categoricalCols = columns.filter((c) => c.inferred_type === "categorical" || c.inferred_type === "text");
  const allCols = columns;

  const generate = () => {
    buildChart.mutate({
      dataset_id: datasetId,
      chart_type: chartType,
      x: NEEDS_X.has(chartType) ? x || undefined : undefined,
      y: NEEDS_Y.has(chartType) ? y || undefined : undefined,
      aggregation: NEEDS_Y.has(chartType) && y ? aggregation : undefined,
      group_by: NEEDS_GROUP.has(chartType) && groupBy ? groupBy : undefined,
      columns: IS_HEATMAP.has(chartType) ? numericCols.map((c) => c.name) : undefined,
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Analysis Builder</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <Field label="Chart type">
            <Select value={chartType} onChange={(e) => setChartType(e.target.value as ChartType)}>
              {CHART_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t.replace("_", " ")}
                </option>
              ))}
            </Select>
          </Field>

          {NEEDS_X.has(chartType) && (
            <Field label="X-axis">
              <Select value={x} onChange={(e) => setX(e.target.value)}>
                <option value="">Select column…</option>
                {(chartType === "bar" || chartType === "grouped_bar" || chartType === "box" ? categoricalCols : allCols).map(
                  (c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  )
                )}
              </Select>
            </Field>
          )}

          {NEEDS_Y.has(chartType) && (
            <Field label="Y-axis">
              <Select value={y} onChange={(e) => setY(e.target.value)}>
                <option value="">Count (no column)</option>
                {numericCols.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </Field>
          )}

          {NEEDS_Y.has(chartType) && y && (
            <Field label="Aggregation">
              <Select value={aggregation} onChange={(e) => setAggregation(e.target.value as Aggregation)}>
                {AGGREGATIONS.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </Select>
            </Field>
          )}

          {NEEDS_GROUP.has(chartType) && (
            <Field label={chartType === "grouped_bar" ? "Group by (required)" : "Group by (optional)"}>
              <Select value={groupBy} onChange={(e) => setGroupBy(e.target.value)}>
                <option value="">None</option>
                {categoricalCols.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </Field>
          )}
        </div>

        <Button onClick={generate} loading={buildChart.isPending}>
          <Wand2 className="h-4 w-4" /> Generate Chart
        </Button>

        {buildChart.isError && (
          <p className="text-xs text-red-400">
            {(buildChart.error as Error)?.message || "Could not build this chart. Check your column selections."}
          </p>
        )}

        {buildChart.data && (
          <div className="rounded-lg border border-border p-3 mt-2">
            <PlotlyChart data={buildChart.data.data} layout={buildChart.data.layout} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-xs text-muted mb-1 block">{label}</label>
      {children}
    </div>
  );
}
