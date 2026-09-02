import { type DragEvent, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, CheckCircle2, FileSpreadsheet, Loader2, UploadCloud } from "lucide-react";
import { useUploadDataset } from "@/hooks/useDatasets";
import { cn } from "@/lib/utils";
import { ApiError } from "@/services/api";

type Status = "idle" | "uploading" | "processing" | "complete" | "failed";

export function UploadDropzone({ onUploaded }: { onUploaded?: (datasetId: string) => void }) {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const upload = useUploadDataset();
  const navigate = useNavigate();

  const handleFile = async (file: File) => {
    setFileName(file.name);
    setError(null);
    setStatus("uploading");
    try {
      // The browser fetch resolves once bytes are sent; the backend then parses
      // and profiles synchronously, so "processing" covers that server-side work.
      setStatus("processing");
      const dataset = await upload.mutateAsync(file);
      setStatus("complete");
      onUploaded?.(dataset.id);
      setTimeout(() => navigate(`/app/datasets/${dataset.id}`), 600);
    } catch (e) {
      const err = e as ApiError;
      setError(err.message || "Upload failed.");
      setStatus("failed");
    }
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) void handleFile(file);
  };

  const busy = status === "uploading" || status === "processing";

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      onClick={() => !busy && inputRef.current?.click()}
      className={cn(
        "rounded-xl border-2 border-dashed p-8 text-center cursor-pointer transition-colors",
        dragOver ? "border-accent bg-accent/5" : "border-border hover:border-accent/50",
        busy && "cursor-wait"
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.xlsx,.xls"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void handleFile(file);
          e.target.value = "";
        }}
      />

      {status === "idle" && (
        <>
          <UploadCloud className="h-8 w-8 mx-auto text-muted mb-3" />
          <p className="text-sm font-medium">Drop a CSV or Excel file, or click to browse</p>
          <p className="text-xs text-muted mt-1">.csv, .xlsx, .xls — up to 200 MB</p>
        </>
      )}
      {busy && (
        <>
          <Loader2 className="h-8 w-8 mx-auto text-accent mb-3 animate-spin" />
          <p className="text-sm font-medium">{status === "uploading" ? "Uploading" : "Validating & profiling"} {fileName}…</p>
          <p className="text-xs text-muted mt-1">This won't take long.</p>
        </>
      )}
      {status === "complete" && (
        <>
          <CheckCircle2 className="h-8 w-8 mx-auto text-emerald-400 mb-3" />
          <p className="text-sm font-medium">{fileName} uploaded</p>
          <p className="text-xs text-muted mt-1">Opening dataset…</p>
        </>
      )}
      {status === "failed" && (
        <>
          <AlertCircle className="h-8 w-8 mx-auto text-red-400 mb-3" />
          <p className="text-sm font-medium">Upload failed</p>
          <p className="text-xs text-red-400/90 mt-1">{error}</p>
          <p className="text-xs text-muted mt-2 flex items-center justify-center gap-1">
            <FileSpreadsheet className="h-3.5 w-3.5" /> Click to try another file
          </p>
        </>
      )}
    </div>
  );
}
