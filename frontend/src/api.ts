import type { Dashboard, DashboardSummary } from "./types";

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

  async createFromFile(file: File, goal: string): Promise<Dashboard> {
    const upload = new FormData();
    upload.append("file", file);
    const dataset = await request<{ id: string }>("/api/datasets", { method: "POST", body: upload });

    const form = new FormData();
    form.append("dataset_id", dataset.id);
    if (goal.trim()) form.append("goal", goal.trim());
    return request<Dashboard>("/api/dashboards", { method: "POST", body: form });
  },

  chat: (id: string, message: string) =>
    request<Dashboard>(`/api/dashboards/${id}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    }),
};
