import { useMemo } from "react";
import Plotly from "plotly.js-dist-min";
import createPlotlyComponent from "react-plotly.js/factory";
import type { PlotlyTrace } from "@/types/api";

const Plot = createPlotlyComponent(Plotly);

const DARK_LAYOUT = {
  paper_bgcolor: "transparent",
  plot_bgcolor: "transparent",
  font: { color: "#cbd5e1", family: "Inter, system-ui, sans-serif", size: 12 },
  margin: { t: 40, r: 20, b: 40, l: 50 },
  colorway: ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#a855f7", "#06b6d4", "#ec4899", "#84cc16"],
  legend: { font: { color: "#cbd5e1" } },
  xaxis: { gridcolor: "rgba(148,163,184,0.15)", zerolinecolor: "rgba(148,163,184,0.25)" },
  yaxis: { gridcolor: "rgba(148,163,184,0.15)", zerolinecolor: "rgba(148,163,184,0.25)" },
};

export function PlotlyChart({
  data,
  layout,
  className,
  height = 320,
}: {
  data: PlotlyTrace[];
  layout?: Record<string, unknown>;
  className?: string;
  height?: number;
}) {
  const mergedLayout = useMemo(
    () => ({
      ...DARK_LAYOUT,
      ...layout,
      title: layout?.title ? { text: layout.title as string, font: { size: 13 } } : undefined,
      xaxis: { ...DARK_LAYOUT.xaxis, ...(layout?.xaxis as object) },
      yaxis: { ...DARK_LAYOUT.yaxis, ...(layout?.yaxis as object) },
      autosize: true,
      height,
    }),
    [layout, height]
  );

  return (
    <div className={className}>
      <Plot
        data={data as Plotly.Data[]}
        layout={mergedLayout as Partial<Plotly.Layout>}
        config={{ responsive: true, displaylogo: false, modeBarButtonsToRemove: ["lasso2d", "select2d"] }}
        useResizeHandler
        style={{ width: "100%", height: `${height}px` }}
      />
    </div>
  );
}
