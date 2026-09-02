import type { ColumnDetail } from "@/types/api";
import { Badge } from "@/components/ui/Badge";
import { formatNumber } from "@/lib/format";

const typeTone: Record<string, "info" | "accent" | "success" | "warning" | "neutral"> = {
  integer: "info",
  float: "info",
  categorical: "accent",
  datetime: "success",
  boolean: "warning",
  text: "neutral",
};

export function ColumnsTable({ columns }: { columns: ColumnDetail[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-xs">
        <thead className="bg-border/30">
          <tr>
            {["Column", "Type", "Role", "Nulls", "Unique", "Min", "Max"].map((h) => (
              <th key={h} className="text-left font-medium px-3 py-2 whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {columns.map((c, i) => (
            <tr key={c.name} className={i % 2 === 1 ? "bg-surface/40" : undefined}>
              <td className="px-3 py-2 font-mono text-[11px] font-medium border-t border-border/60">{c.name}</td>
              <td className="px-3 py-2 border-t border-border/60">
                <Badge tone={typeTone[c.inferred_type] ?? "neutral"}>{c.inferred_type}</Badge>
              </td>
              <td className="px-3 py-2 border-t border-border/60 text-muted">{c.logical_type ?? "—"}</td>
              <td className="px-3 py-2 border-t border-border/60 tabular-nums">{formatNumber(c.null_count)}</td>
              <td className="px-3 py-2 border-t border-border/60 tabular-nums">{formatNumber(c.unique_count)}</td>
              <td className="px-3 py-2 border-t border-border/60 font-mono text-[11px]">{c.min_value ?? "—"}</td>
              <td className="px-3 py-2 border-t border-border/60 font-mono text-[11px]">{c.max_value ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
