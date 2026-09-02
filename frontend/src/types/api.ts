// Types mirroring backend Pydantic schemas (app/schemas/*.py).

export interface Dataset {
  id: string;
  original_filename: string;
  file_size_bytes: number;
  mime_type: string | null;
  row_count: number | null;
  column_count: number | null;
  status: "uploaded" | "processing" | "ready" | "failed";
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ColumnOut {
  name: string;
  position: number;
  inferred_type: string;
  null_count: number;
  unique_count: number;
}

export interface DatasetDetail extends Dataset {
  columns: ColumnOut[];
}

export interface ColumnDetail {
  name: string;
  position: number;
  inferred_type: string;
  logical_type: string | null;
  null_count: number;
  unique_count: number;
  min_value: string | null;
  max_value: string | null;
  stats: {
    numeric: NumericStats | null;
    categorical: CategoricalStats | null;
    datetime: DatetimeStats | null;
    boolean: BooleanStats | null;
  } | null;
}

export interface PreviewPage {
  columns: string[];
  rows: Record<string, unknown>[];
  page: number;
  page_size: number;
  total_rows: number;
  total_pages: number;
}

export interface NumericStats {
  count: number;
  mean: number | null;
  median: number | null;
  std: number | null;
  min: number | null;
  max: number | null;
  q1: number | null;
  q3: number | null;
  skewness: number | null;
  outlier_count: number;
  outlier_percentage: number;
}

export interface CategoryCount {
  value: string;
  count: number;
  percentage: number;
}

export interface CategoricalStats {
  distinct_count: number;
  top_categories: CategoryCount[];
}

export interface DatetimeStats {
  min_date: string | null;
  max_date: string | null;
  range_days: number | null;
  invalid_count: number;
  invalid_percentage: number;
}

export interface BooleanStats {
  true_count: number;
  false_count: number;
}

export interface ColumnProfile {
  name: string;
  position: number;
  inferred_type: string;
  logical_type: string;
  null_count: number;
  null_percentage: number;
  unique_count: number;
  cardinality_ratio: number;
  min_value: string | null;
  max_value: string | null;
  numeric: NumericStats | null;
  categorical: CategoricalStats | null;
  datetime: DatetimeStats | null;
  boolean: BooleanStats | null;
}

export interface Issue {
  type: string;
  column: string | null;
  severity: "info" | "low" | "medium" | "high";
  message: string;
}

export interface QualityScore {
  overall: number;
  completeness: number;
  missing_values: number;
  duplicates: number;
  data_types: number;
  outliers: number;
}

export interface DatasetProfile {
  dataset_id: string;
  row_count: number;
  column_count: number;
  missing_cells: number;
  missing_percentage: number;
  duplicate_rows: number;
  duplicate_percentage: number;
  columns: ColumnProfile[];
  issues: Issue[];
  quality: QualityScore;
  generated_at: string;
  cached: boolean;
}

// --- Analysis ---

export type FilterOperator = "eq" | "ne" | "gt" | "gte" | "lt" | "lte" | "in" | "not_in" | "contains" | "is_null" | "not_null";
export type Aggregation = "sum" | "mean" | "median" | "count" | "min" | "max" | "std";

export interface AnalysisFilter {
  column: string;
  operator: FilterOperator;
  value?: unknown;
}

export interface AnalysisMetric {
  column?: string | null;
  aggregation: Aggregation;
  alias?: string | null;
}

export interface AnalysisSort {
  by: string;
  direction: "asc" | "desc";
}

export interface AnalysisRequest {
  dataset_id: string;
  filters?: AnalysisFilter[];
  group_by?: string[];
  metrics?: AnalysisMetric[];
  sort?: AnalysisSort | null;
  limit?: number | null;
  session_id?: string | null;
  title?: string | null;
}

export interface AnalysisResultOut {
  session_id: string;
  result_id: string;
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  total_matched_rows: number;
  truncated: boolean;
  spec: Record<string, unknown>;
}

export interface CorrelationResult {
  columns: string[];
  matrix: (number | null)[][];
  strong_pairs: { column_a: string; column_b: string; correlation: number }[];
  method: string;
}

export interface OutlierColumnResult {
  column: string;
  method: string;
  outlier_count: number;
  outlier_percentage: number;
  sample_rows: Record<string, unknown>[];
}

export interface OutlierResult {
  method: string;
  columns: OutlierColumnResult[];
}

// --- Charts ---

export type ChartType = "bar" | "grouped_bar" | "line" | "area" | "scatter" | "histogram" | "box" | "heatmap" | "pie";

export interface ChartRequest {
  dataset_id: string;
  chart_type: ChartType;
  x?: string | null;
  y?: string | null;
  aggregation?: Aggregation | null;
  group_by?: string | null;
  columns?: string[] | null;
  filters?: AnalysisFilter[];
  limit?: number | null;
  bins?: number | null;
  title?: string | null;
  session_id?: string | null;
}

export interface PlotlyTrace {
  type: string;
  [key: string]: unknown;
}

export interface ChartResult {
  session_id: string;
  result_id: string;
  chart_type: string;
  data: PlotlyTrace[];
  layout: Record<string, unknown>;
  row_count: number;
  truncated: boolean;
  granularity: string | null;
  spec: Record<string, unknown>;
}

export interface EDAChart {
  chart_type: string;
  data: PlotlyTrace[];
  layout: Record<string, unknown>;
  row_count: number;
  truncated: boolean;
  granularity: string | null;
  reason: string;
}

export interface EDASuggestionsResponse {
  dataset_id: string;
  charts: EDAChart[];
}

// --- AI Chat ---

export interface ToolCallTrace {
  name: string;
  arguments: Record<string, unknown>;
  result: Record<string, unknown>;
}

export interface ChatMessageOut {
  role: string;
  content: string;
}

export interface ChatResponse {
  session_id: string;
  message: ChatMessageOut;
  tool_calls: ToolCallTrace[];
  charts: ChartLikeSpec[];
}

export interface ChartLikeSpec {
  chart_type: string;
  data: PlotlyTrace[];
  layout: Record<string, unknown>;
  row_count: number;
  truncated: boolean;
  granularity: string | null;
}

export interface StoredChatMessage {
  id: string;
  role: string;
  content: string;
  tool_name: string | null;
  tool_args: Record<string, unknown> | null;
  tool_result: Record<string, unknown> | null;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  llm_configured: boolean;
  db: { ok: boolean; detail: string | null };
  storage: { backend: string; root: string; writable: boolean };
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}
