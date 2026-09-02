import { Suspense, lazy } from "react";
import type { PlotlyTrace } from "@/types/api";
import { Skeleton } from "@/components/ui/Skeleton";

// Plotly.js is large (~1MB+ gzipped) — load it only when a chart actually
// needs to render, instead of blocking the initial app bundle.
const PlotlyChartImpl = lazy(() =>
  import("./PlotlyChartImpl").then((m) => ({ default: m.PlotlyChart }))
);

export function PlotlyChart(props: {
  data: PlotlyTrace[];
  layout?: Record<string, unknown>;
  className?: string;
  height?: number;
}) {
  return (
    <Suspense fallback={<Skeleton className={props.className} style={{ height: props.height ?? 320 }} />}>
      <PlotlyChartImpl {...props} />
    </Suspense>
  );
}
