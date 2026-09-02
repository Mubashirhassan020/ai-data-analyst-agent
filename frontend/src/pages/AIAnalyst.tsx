import { useState } from "react";
import { MessageSquare } from "lucide-react";
import { useDatasets } from "@/hooks/useDatasets";
import { Select } from "@/components/ui/Input";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/States";
import { AIChatPanel } from "@/components/chat/AIChatPanel";

export default function AIAnalyst() {
  const { data: datasets, isLoading, isError, refetch } = useDatasets();
  const [selected, setSelected] = useState<string>("");

  const readyDatasets = datasets?.filter((d) => d.status === "ready") ?? [];
  const activeId = selected || readyDatasets[0]?.id;

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-muted">Dataset</h2>
        {readyDatasets.length > 0 && (
          <Select className="w-64" value={activeId} onChange={(e) => setSelected(e.target.value)}>
            {readyDatasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.original_filename}
              </option>
            ))}
          </Select>
        )}
      </div>

      {isLoading ? (
        <LoadingState />
      ) : isError ? (
        <ErrorState description="Could not load datasets." onRetry={() => refetch()} />
      ) : readyDatasets.length === 0 ? (
        <EmptyState
          icon={<MessageSquare className="h-6 w-6" />}
          title="Upload a dataset first"
          description="The AI analyst needs a dataset to answer questions about. Upload one from the Datasets page."
        />
      ) : activeId ? (
        <AIChatPanel datasetId={activeId} />
      ) : null}
    </div>
  );
}
