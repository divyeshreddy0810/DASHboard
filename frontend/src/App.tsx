import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { SlotContext, assignSlots, type SlotMap } from "./colors";
import { ChartCard } from "./components/ChartCard";
import { ChatPanel } from "./components/ChatPanel";
import { UploadForm } from "./components/UploadForm";
import type { Dashboard, DashboardSummary } from "./types";

function dashboardIdFromHash(): string | null {
  const m = window.location.hash.match(/^#\/d\/([\w-]+)/);
  return m ? m[1] : null;
}

export default function App() {
  const [currentId, setCurrentId] = useState<string | null>(dashboardIdFromHash);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [recent, setRecent] = useState<DashboardSummary[]>([]);
  const [planner, setPlanner] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const slots = useRef<{ id: string; map: SlotMap }>({ id: "", map: new Map() });

  if (dashboard && slots.current.id !== dashboard.id) {
    slots.current = { id: dashboard.id, map: new Map() };
  }
  if (dashboard) {
    slots.current.map = assignSlots(dashboard.charts, slots.current.map);
  }

  useEffect(() => {
    const onHash = () => setCurrentId(dashboardIdFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    api.health().then((h) => setPlanner(h.planner)).catch(() => setPlanner(""));
    api.listDashboards().then(setRecent).catch(() => setRecent([]));
  }, [currentId]);

  useEffect(() => {
    setError(null);
    if (!currentId) {
      setDashboard(null);
      return;
    }
    api.getDashboard(currentId).then(setDashboard).catch((e: Error) => setError(e.message));
  }, [currentId]);

  const run = useCallback(async (fn: () => Promise<Dashboard>) => {
    setBusy(true);
    setError(null);
    try {
      const d = await fn();
      setDashboard(d);
      window.location.hash = `#/d/${d.id}`;
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, []);

  return (
    <div className="app">
      <header className="topbar">
        <a href="#/" className="brand">Dashboard</a>
        {planner && <span className="planner">planner: {planner}</span>}
      </header>

      {error && <div className="error" role="alert">{error}</div>}

      {!currentId && (
        <main className="home">
          <h1>Build a dashboard from a file</h1>
          <p className="lede">Upload a dataset. The app profiles each column, picks the charts, and you can refine them by chat.</p>
          <UploadForm busy={busy} onSubmit={(file, goal) => run(() => api.createFromFile(file, goal))} />
          {recent.length > 0 && (
            <section className="recent">
              <h2>Recent dashboards</h2>
              <ul>
                {recent.map((d) => (
                  <li key={d.id}>
                    <a href={`#/d/${d.id}`}>{d.title}</a>
                    <time>{new Date(d.updated_at).toLocaleString()}</time>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </main>
      )}

      {currentId && dashboard && (
        <div className="workspace">
          <main className="board">
            <div className="board-head">
              <h1>{dashboard.title}</h1>
              {dashboard.description && <p>{dashboard.description}</p>}
            </div>
            <SlotContext.Provider value={slots.current.map}>
              <div className="grid">
                {dashboard.charts.map((c) => (
                  <ChartCard key={c.spec.id} chart={c} />
                ))}
              </div>
            </SlotContext.Provider>
          </main>
          <ChatPanel
            history={dashboard.history}
            busy={busy}
            disabled={planner === "heuristic" ? "Chat editing needs ANTHROPIC_API_KEY set on the backend." : undefined}
            onSend={(m) => run(() => api.chat(dashboard.id, m))}
          />
        </div>
      )}
    </div>
  );
}
