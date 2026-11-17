import type { ChartSpec, Dashboard, DashboardSummary } from "./types";

function json(method: string, body: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      // non-JSON error body
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ ok: boolean; planner: string }>("/api/health"),

  listDashboards: () => request<DashboardSummary[]>("/api/dashboards"),

  getDashboard: (id: string) => request<Dashboard>(`/api/dashboards/${id}`),

  async createFromFile(file: File, title: string, goal: string): Promise<Dashboard> {
    const upload = new FormData();
    upload.append("file", file);
    const dataset = await request<{ id: string }>("/api/datasets", { method: "POST", body: upload });

    const form = new FormData();
    form.append("dataset_id", dataset.id);
    if (title.trim()) form.append("title", title.trim());
    if (goal.trim()) form.append("goal", goal.trim());
    return request<Dashboard>("/api/dashboards", { method: "POST", body: form });
  },

  rename: (id: string, title: string) => request<Dashboard>(`/api/dashboards/${id}`, json("PATCH", { title })),

  chat: (id: string, message: string) => request<Dashboard>(`/api/dashboards/${id}/chat`, json("POST", { message })),

  suggestions: (id: string) => request<ChartSpec[]>(`/api/dashboards/${id}/suggestions`),

  addChart: (id: string, chart: ChartSpec, index?: number) =>
    request<Dashboard>(`/api/dashboards/${id}/charts`, json("POST", { chart, index })),

  moveChart: (id: string, chartId: string, index: number) =>
    request<Dashboard>(`/api/dashboards/${id}/charts/${encodeURIComponent(chartId)}/move`, json("POST", { index })),

  removeChart: (id: string, chartId: string) =>
    request<Dashboard>(`/api/dashboards/${id}/charts/${encodeURIComponent(chartId)}`, { method: "DELETE" }),
};
