import { useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { useDatasetPreview } from "@/hooks/useDatasets";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/States";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

export function DataPreviewTable({ datasetId }: { datasetId: string }) {
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [sort, setSort] = useState<string | undefined>();
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");

  const { data, isLoading, isError, refetch, isFetching } = useDatasetPreview(datasetId, {
    page,
    page_size: pageSize,
    sort,
    sort_dir: sortDir,
    search: search || undefined,
  });

  const toggleSort = (col: string) => {
    if (sort !== col) {
      setSort(col);
      setSortDir("asc");
    } else if (sortDir === "asc") {
      setSortDir("desc");
    } else {
      setSort(undefined);
    }
    setPage(1);
  };

  if (isLoading) return <LoadingState label="Loading preview…" />;
  if (isError) return <ErrorState description="Could not load the data preview." onRetry={() => refetch()} />;
  if (!data) return null;

  return (
    <div className="space-y-3">
      <form
        className="flex items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          setSearch(searchInput);
          setPage(1);
        }}
      >
        <div className="relative flex-1 max-w-xs">
          <Search className="h-3.5 w-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
          <Input
            placeholder="Search all columns…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-8"
          />
        </div>
        <Button type="submit" variant="secondary" size="sm">
          Search
        </Button>
        <span className="text-xs text-muted ml-auto">
          {data.total_rows.toLocaleString()} row{data.total_rows === 1 ? "" : "s"} matched
          {isFetching && " · refreshing…"}
        </span>
      </form>

      {data.rows.length === 0 ? (
        <EmptyState title="No matching rows" description="Try a different search term." />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-xs">
            <thead className="bg-border/30 sticky top-0">
              <tr>
                {data.columns.map((col) => (
                  <th
                    key={col}
                    onClick={() => toggleSort(col)}
                    className="text-left font-medium px-3 py-2 whitespace-nowrap cursor-pointer select-none hover:text-accent"
                  >
                    <span className="inline-flex items-center gap-1">
                      {col}
                      {sort === col ? (
                        sortDir === "asc" ? (
                          <ArrowUp className="h-3 w-3" />
                        ) : (
                          <ArrowDown className="h-3 w-3" />
                        )
                      ) : (
                        <ArrowUpDown className="h-3 w-3 opacity-30" />
                      )}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row, i) => (
                <tr key={i} className={cn("border-t border-border/60", i % 2 === 1 && "bg-surface/40")}>
                  {data.columns.map((col) => (
                    <td key={col} className="px-3 py-1.5 whitespace-nowrap font-mono text-[11px] text-fg/90">
                      {row[col] === null || row[col] === undefined ? (
                        <span className="text-muted italic">null</span>
                      ) : (
                        String(row[col])
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-muted">
        <span>
          Page {data.page} of {data.total_pages}
        </span>
        <div className="flex items-center gap-1">
          <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            <ChevronLeft className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={page >= data.total_pages}
            onClick={() => setPage((p) => p + 1)}
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
