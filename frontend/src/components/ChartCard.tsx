import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCompact, formatFull } from "../format";
import { useTheme, type Theme } from "../theme";
import type { ChartData, RenderedChart } from "../types";

const HEIGHT = 260;

function axisProps(theme: Theme) {
  return {
    stroke: theme.axis,
    tick: { fill: theme.muted, fontSize: 12 },
    tickLine: false,
  };
}

function tooltipProps(theme: Theme) {
  return {
    formatter: (v: unknown) => formatFull(v),
    contentStyle: {
      background: theme.surface,
      border: `1px solid ${theme.grid}`,
      borderRadius: 8,
      fontSize: 12,
      color: theme.text,
    },
    labelStyle: { color: theme.text, fontWeight: 600 },
  };
}

function Kpi({ data }: { data: ChartData }) {
  return (
    <div className="kpi">
      <div className="kpi-value" title={formatFull(data.value)}>
        {formatCompact(data.value)}
      </div>
    </div>
  );
}

function Categorical({ chart, data, theme }: { chart: RenderedChart["spec"]; data: ChartData; theme: Theme }) {
  const keys = data.keys ?? [];
  const rows = data.rows ?? [];
  const color = (k: string, i: number) => theme.series[keys.length > 1 ? (data.slots?.[k] ?? i) % 8 : 0];
  const showLegend = keys.length > 1;
  const common = { data: rows, margin: { top: 8, right: 12, bottom: 4, left: 0 } };
  const grid = <CartesianGrid stroke={theme.grid} vertical={false} />;
  const x = <XAxis dataKey="x" {...axisProps(theme)} minTickGap={16} />;
  const y = <YAxis {...axisProps(theme)} axisLine={false} tickFormatter={formatCompact} width={52} />;
  const tip = <Tooltip {...tooltipProps(theme)} cursor={{ fill: theme.grid, fillOpacity: 0.4 }} />;
  const legend = showLegend ? <Legend wrapperStyle={{ fontSize: 12 }} iconType="circle" iconSize={8} /> : null;

  if (chart.type === "line") {
    return (
      <LineChart {...common}>
        {grid}{x}{y}
        <Tooltip {...tooltipProps(theme)} cursor={{ stroke: theme.axis }} />
        {legend}
        {keys.map((k, i) => (
          <Line key={k} dataKey={k} stroke={color(k, i)} strokeWidth={2} dot={false}
                activeDot={{ r: 4, stroke: theme.surface, strokeWidth: 2 }} isAnimationActive={false} />
        ))}
      </LineChart>
    );
  }
  if (chart.type === "area") {
    return (
      <AreaChart {...common}>
        {grid}{x}{y}
        <Tooltip {...tooltipProps(theme)} cursor={{ stroke: theme.axis }} />
        {legend}
        {keys.map((k, i) => (
          <Area key={k} dataKey={k} stackId="a" stroke={color(k, i)} fill={color(k, i)}
                fillOpacity={0.25} strokeWidth={2} isAnimationActive={false} />
        ))}
      </AreaChart>
    );
  }
  const stacked = keys.length > 3;
  return (
    <BarChart {...common} barCategoryGap={chart.type === "histogram" ? 1 : "20%"}>
      {grid}{x}{y}{tip}{legend}
      {keys.map((k, i) => (
        <Bar key={k} dataKey={k} fill={color(k, i)} stackId={stacked ? "s" : undefined}
             radius={stacked && i < keys.length - 1 ? 0 : [4, 4, 0, 0]} maxBarSize={48}
             stroke={stacked ? theme.surface : undefined} strokeWidth={stacked ? 1 : 0}
             isAnimationActive={false} />
      ))}
    </BarChart>
  );
}

function Donut({ data, theme }: { data: ChartData; theme: Theme }) {
  const key = data.keys?.[0] ?? "value";
  const rows = data.rows ?? [];
  return (
    <PieChart>
      <Tooltip {...tooltipProps(theme)} />
      <Legend wrapperStyle={{ fontSize: 12 }} iconType="circle" iconSize={8} />
      <Pie data={rows} dataKey={key} nameKey="x" innerRadius="55%" outerRadius="85%"
           stroke={theme.surface} strokeWidth={2} isAnimationActive={false}>
        {rows.map((r, i) => (
          <Cell key={i} fill={theme.series[(data.slots?.[String(r.x)] ?? i) % 8]} />
        ))}
      </Pie>
    </PieChart>
  );
}

function ScatterPlot({ chart, data, theme }: { chart: RenderedChart["spec"]; data: ChartData; theme: Theme }) {
  const keys = data.keys ?? [];
  const points = data.points ?? [];
  return (
    <ScatterChart margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
      <CartesianGrid stroke={theme.grid} />
      <XAxis type="number" dataKey="x" name={chart.x ?? "x"} {...axisProps(theme)} tickFormatter={formatCompact} />
      <YAxis type="number" dataKey="y" name={chart.y ?? "y"} {...axisProps(theme)} axisLine={false}
             tickFormatter={formatCompact} width={52} />
      <Tooltip {...tooltipProps(theme)} cursor={{ strokeDasharray: "3 3", stroke: theme.axis }} />
      {keys.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} iconType="circle" iconSize={8} />}
      {keys.map((k, i) => (
        <Scatter key={k} name={k} data={points.filter((p) => p.series === k)} fill={theme.series[keys.length > 1 ? (data.slots?.[k] ?? i) % 8 : 0]}
                 fillOpacity={0.7} isAnimationActive={false} />
      ))}
    </ScatterChart>
  );
}

function DataTable({ data }: { data: ChartData }) {
  const columns = data.columns ?? [];
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {(data.rows ?? []).map((r, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td key={c} className={typeof r[c] === "number" ? "num" : undefined}>{formatFull(r[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface CardProps {
  chart: RenderedChart;
  onRemove?: () => void;
  onDragStart?: (e: React.DragEvent) => void;
}

export function ChartCard({ chart, onRemove, onDragStart }: CardProps) {
  const theme = useTheme();
  const { spec, data, error } = chart;

  let body: React.ReactNode;
  if (error || !data) {
    body = <p className="chart-error">{error ?? "No data."}</p>;
  } else if (spec.type === "kpi") {
    body = <Kpi data={data} />;
  } else if (spec.type === "table") {
    body = <DataTable data={data} />;
  } else if ((data.rows?.length ?? 0) === 0 && (data.points?.length ?? 0) === 0) {
    body = <p className="chart-empty">No rows match this chart.</p>;
  } else {
    const plot =
      spec.type === "pie" ? <Donut data={data} theme={theme} />
      : spec.type === "scatter" ? <ScatterPlot chart={spec} data={data} theme={theme} />
      : <Categorical chart={spec} data={data} theme={theme} />;
    body = (
      <div style={{ height: HEIGHT }}>
        <ResponsiveContainer width="100%" height="100%">{plot}</ResponsiveContainer>
      </div>
    );
  }

  return (
    <section className={`card type-${spec.type}`}>
      <header draggable={!!onDragStart} onDragStart={onDragStart} className={onDragStart ? "handle" : undefined}>
        <h3 title={spec.rationale}>{spec.title}</h3>
        <div className="card-tools">
          {data?.truncated && <span className="badge">top {data.rows?.length}</span>}
          {onRemove && (
            <button type="button" className="icon" aria-label={`Remove ${spec.title}`} onClick={onRemove}>
              ×
            </button>
          )}
        </div>
      </header>
      {body}
    </section>
  );
}
