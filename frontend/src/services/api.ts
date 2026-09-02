import type {
  AnalysisRequest,
  AnalysisResultOut,
  ChartRequest,
  ChartResult,
  ChatResponse,
  CorrelationResult,
  DatasetDetail,
  DatasetProfile,
  Dataset,
  ColumnDetail,
  EDASuggestionsResponse,
  HealthResponse,
  OutlierResult,
  PreviewPage,
  StoredChatMessage,
} from "@/types/api";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  code: string;
  details?: Record<string, unknown>;
  status: number;

  constructor(status: number, code: string, message: string, details?: Record<string, unknown>) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let code = "http_error";
    let message = res.statusText || `Request failed (${res.status})`;
    let details: Record<string, unknown> | undefined;
    try {
      const body = await res.json();
      if (body?.error) {
        code = body.error.code ?? code;
        message = body.error.message ?? message;
        details = body.error.details;
      }
    } catch {
      /* body wasn't JSON; keep defaults */
    }
    throw new ApiError(res.status, code, message, details);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export const api = {
  health: () => request<HealthResponse>("/health"),

  // Datasets
  uploadDataset: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Dataset>("/datasets/upload", { method: "POST", body: form });
  },
  listDatasets: () => request<Dataset[]>("/datasets"),
  getDataset: (id: string) => request<DatasetDetail>(`/datasets/${id}`),
  deleteDataset: (id: string) => request<void>(`/datasets/${id}`, { method: "DELETE" }),
  previewDataset: (
    id: string,
    opts: { page?: number; page_size?: number; sort?: string; sort_dir?: "asc" | "desc"; search?: string } = {}
  ) => request<PreviewPage>(`/datasets/${id}/preview${qs(opts)}`),
  getDatasetProfile: (id: string, refresh = false) =>
    request<DatasetProfile>(`/datasets/${id}/profile${qs({ refresh })}`),
  getDatasetColumns: (id: string) => request<ColumnDetail[]>(`/datasets/${id}/columns`),
  getEdaSuggestions: (id: string) => request<EDASuggestionsResponse>(`/datasets/${id}/eda-suggestions`),

  // Analysis
  executeAnalysis: (payload: AnalysisRequest) =>
    request<AnalysisResultOut>("/analysis/execute", { method: "POST", body: JSON.stringify(payload) }),
  buildChart: (payload: ChartRequest) =>
    request<ChartResult>("/analysis/chart", { method: "POST", body: JSON.stringify(payload) }),
  correlation: (dataset_id: string, columns?: string[], method = "pearson") =>
    request<CorrelationResult>("/analysis/correlation", {
      method: "POST",
      body: JSON.stringify({ dataset_id, columns, method }),
    }),
  outliers: (dataset_id: string, columns?: string[], method = "iqr") =>
    request<OutlierResult>("/analysis/outliers", {
      method: "POST",
      body: JSON.stringify({ dataset_id, columns, method }),
    }),

  // AI
  chat: (dataset_id: string, message: string, session_id?: string | null) =>
    request<ChatResponse>("/ai/chat", {
      method: "POST",
      body: JSON.stringify({ dataset_id, message, session_id: session_id ?? null }),
    }),
  analyze: (dataset_id: string, session_id?: string | null) =>
    request<ChatResponse>("/ai/analyze", {
      method: "POST",
      body: JSON.stringify({ dataset_id, session_id: session_id ?? null }),
    }),
  getChatMessages: (sessionId: string) => request<StoredChatMessage[]>(`/ai/sessions/${sessionId}/messages`),
};
