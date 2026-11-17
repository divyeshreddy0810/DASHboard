import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { Board } from "./components/Board";
import { ChatPanel } from "./components/ChatPanel";
import { Suggestions } from "./components/Suggestions";
import { TitleEditor } from "./components/TitleEditor";
import { UploadForm } from "./components/UploadForm";
import type { ChartSpec, Dashboard, DashboardSummary } from "./types";

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
  const [suggestions, setSuggestions] = useState<ChartSpec[] | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  useEffect(() => {
    if (!dashboard) return;
    let stale = false;
    api
      .suggestions(dashboard.id)
      .then((items) => !stale && setSuggestions(items))
      .catch(() => !stale && setSuggestions([]));
    return () => {
      stale = true;
    };
  }, [dashboard?.id, dashboard?.updated_at]);

  const apply = useCallback(async (fn: () => Promise<Dashboard>) => {
    setError(null);
    try {
      setDashboard(await fn());
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

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
        {currentId && dashboard ? (
          <div className="topbar-title">
            <a href="#/" className="back" aria-label="All dashboards">←</a>
            <TitleEditor
              value={dashboard.title}
              onSave={async (title) => {
                try {
                  setDashboard(await api.rename(dashboard.id, title));
                } catch (e) {
                  setError((e as Error).message);
                  throw e;
                }
              }}
            />
          </div>
        ) : (
          <a href="#/" className="brand">Dashboard</a>
        )}
        {planner && <span className="planner">planner: {planner}</span>}
      </header>

      {error && <div className="error" role="alert">{error}</div>}

      {!currentId && (
        <main className="home">
          <h1>Build a dashboard from a file</h1>
          <p className="lede">Upload a dataset. The app profiles each column, picks the charts, and you can refine them by chat.</p>
          <UploadForm busy={busy} onSubmit={(file, title, goal) => run(() => api.createFromFile(file, title, goal))} />
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
            {dashboard.description && <p className="board-desc">{dashboard.description}</p>}
            <Board
              charts={dashboard.charts}
              onAdd={(chart, index) => apply(() => api.addChart(dashboard.id, chart, index))}
              onMove={(chartId, index) => apply(() => api.moveChart(dashboard.id, chartId, index))}
              onRemove={(chartId) => apply(() => api.removeChart(dashboard.id, chartId))}
            />
          </main>
          <aside className="side">
            <Suggestions
              items={suggestions}
              busy={busy}
              onAdd={(chart) => apply(() => api.addChart(dashboard.id, chart))}
            />
            <ChatPanel
              history={dashboard.history}
              busy={busy}
              disabled={planner === "heuristic" ? "Chat editing needs ANTHROPIC_API_KEY set on the backend." : undefined}
              onSend={(m) => run(() => api.chat(dashboard.id, m))}
            />
          </aside>
        </div>
      )}
    </div>
  );
}
