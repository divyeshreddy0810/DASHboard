export type ChartType = "kpi" | "bar" | "line" | "area" | "pie" | "scatter" | "histogram" | "table";

export interface ChartSpec {
  id: string;
  type: ChartType;
  title: string;
  x: string | null;
  y: string | null;
  agg: string;
  series: string | null;
  time_grain: string | null;
  limit: number | null;
  width: "third" | "half" | "full";
  rationale: string;
}

export type Row = Record<string, string | number | null>;

export interface ChartData {
  value?: number | null;
  label?: string;
  keys?: string[];
  rows?: Row[];
  points?: { x: number; y: number; series: string }[];
  columns?: string[];
  truncated?: boolean;
}

export interface RenderedChart {
  spec: ChartSpec;
  data: ChartData | null;
  error: string | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface Dashboard {
  id: string;
  dataset_id: string;
  title: string;
  description: string;
  charts: RenderedChart[];
  history: ChatMessage[];
  planner: string;
  updated_at: string;
}

export interface DashboardSummary {
  id: string;
  title: string;
  dataset_id: string;
  updated_at: string;
}
