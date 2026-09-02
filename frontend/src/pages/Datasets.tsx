import { useState } from "react";
import { Link } from "react-router-dom";
import { Database, Trash2 } from "lucide-react";
import { useDatasets, useDeleteDataset } from "@/hooks/useDatasets";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { UploadDropzone } from "@/components/upload/UploadDropzone";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/States";
import { formatBytes, formatDate, formatNumber } from "@/lib/format";

const statusTone = { ready: "success", processing: "warning", uploaded: "info", failed: "danger" } as const;

export default function Datasets() {
  const { data: datasets, isLoading, isError, refetch } = useDatasets();
  const deleteMutation = useDeleteDataset();
  const [confirmingId, setConfirmingId] = useState<string | null>(null);

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Upload a dataset</CardTitle>
        </CardHeader>
        <CardContent>
          <UploadDropzone />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>All Datasets</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <LoadingState />
          ) : isError ? (
            <ErrorState description="Could not load datasets." onRetry={() => refetch()} />
          ) : !datasets || datasets.length === 0 ? (
            <EmptyState icon={<Database className="h-6 w-6" />} title="No datasets yet" description="Upload one above." />
          ) : (
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full text-sm">
                <thead className="bg-border/30 text-xs">
                  <tr>
                    {["Name", "Rows", "Columns", "Size", "Status", "Uploaded", ""].map((h) => (
                      <th key={h} className="text-left font-medium px-3 py-2">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {datasets.map((d, i) => (
                    <tr key={d.id} className={i % 2 === 1 ? "bg-surface/40" : undefined}>
                      <td className="px-3 py-2.5 border-t border-border/60">
                        <Link to={`/app/datasets/${d.id}`} className="font-medium hover:text-accent">
                          {d.original_filename}
                        </Link>
                        {d.error_message && <p className="text-xs text-red-400 mt-0.5">{d.error_message}</p>}
                      </td>
                      <td className="px-3 py-2.5 border-t border-border/60 tabular-nums text-xs">{formatNumber(d.row_count)}</td>
                      <td className="px-3 py-2.5 border-t border-border/60 tabular-nums text-xs">{formatNumber(d.column_count)}</td>
                      <td className="px-3 py-2.5 border-t border-border/60 text-xs text-muted">{formatBytes(d.file_size_bytes)}</td>
                      <td className="px-3 py-2.5 border-t border-border/60">
                        <Badge tone={statusTone[d.status]}>{d.status}</Badge>
                      </td>
                      <td className="px-3 py-2.5 border-t border-border/60 text-xs text-muted">{formatDate(d.created_at)}</td>
                      <td className="px-3 py-2.5 border-t border-border/60 text-right">
                        {confirmingId === d.id ? (
                          <div className="flex items-center gap-1.5 justify-end">
                            <Button
                              size="sm"
                              variant="danger"
                              loading={deleteMutation.isPending}
                              onClick={() => deleteMutation.mutate(d.id, { onSettled: () => setConfirmingId(null) })}
                            >
                              Confirm
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => setConfirmingId(null)}>
                              Cancel
                            </Button>
                          </div>
                        ) : (
                          <Button size="sm" variant="ghost" onClick={() => setConfirmingId(d.id)}>
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
