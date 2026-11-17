import { SUGGESTION_MIME } from "../dnd";
import type { ChartSpec } from "../types";

const TYPE_LABEL: Record<string, string> = {
  kpi: "KPI",
  bar: "Bar",
  line: "Trend",
  area: "Area",
  pie: "Share",
  scatter: "Scatter",
  histogram: "Distribution",
  table: "Table",
};

interface Props {
  items: ChartSpec[] | null;
  busy: boolean;
  onAdd: (chart: ChartSpec) => void;
}

export function Suggestions({ items, busy, onAdd }: Props) {
  return (
    <section className="suggest">
      <h2>Suggested comparisons</h2>
      <p className="hint">Drag one onto the dashboard, or press + to add it at the end.</p>
      {items === null ? (
        <p className="hint">Loading…</p>
      ) : items.length === 0 ? (
        <p className="hint">No more suggestions for this data.</p>
      ) : (
        <ul>
          {items.map((c) => (
            <li
              key={c.id}
              draggable={!busy}
              title={c.rationale}
              onDragStart={(e) => {
                e.dataTransfer.setData(SUGGESTION_MIME, JSON.stringify(c));
                e.dataTransfer.effectAllowed = "copy";
              }}
            >
              <span className={`tag tag-${c.type}`}>{TYPE_LABEL[c.type] ?? c.type}</span>
              <span className="suggest-title">{c.title}</span>
              <button type="button" aria-label={`Add ${c.title}`} disabled={busy} onClick={() => onAdd(c)}>
                +
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
