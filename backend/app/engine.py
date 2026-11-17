"""Compute chart data from a ChartSpec and a DataFrame."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .spec import ChartSpec, Filter

MAX_CATEGORIES = 25
MAX_SCATTER_POINTS = 1500
MAX_TABLE_ROWS = 200
PERIOD = {"day": "D", "week": "W", "month": "M", "quarter": "Q", "year": "Y"}


class ChartError(ValueError):
    pass


def _require(df: pd.DataFrame, *cols: str | None) -> None:
    missing = [c for c in cols if c and c not in df.columns]
    if missing:
        raise ChartError(f"Unknown column(s): {', '.join(missing)}")


def _cast(series: pd.Series, raw: str) -> Any:
    if pd.api.types.is_numeric_dtype(series):
        try:
            return float(raw)
        except ValueError as exc:
            raise ChartError(f"'{raw}' is not a number for column {series.name}") from exc
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.Timestamp(raw)
    return raw


def apply_filters(df: pd.DataFrame, filters: List[Filter]) -> pd.DataFrame:
    for f in filters:
        _require(df, f.column)
        s = df[f.column]
        if not f.values:
            continue
        if f.op in ("in", "not_in"):
            vals = [_cast(s, v) for v in f.values]
            mask = s.isin(vals) if not pd.api.types.is_object_dtype(s) else s.astype(str).isin(f.values)
            df = df[mask if f.op == "in" else ~mask]
            continue
        v = _cast(s, f.values[0])
        if f.op == "eq":
            df = df[s.astype(str) == f.values[0]] if isinstance(v, str) else df[s == v]
        elif f.op == "neq":
            df = df[s.astype(str) != f.values[0]] if isinstance(v, str) else df[s != v]
        elif f.op == "gt":
            df = df[s > v]
        elif f.op == "gte":
            df = df[s >= v]
        elif f.op == "lt":
            df = df[s < v]
        elif f.op == "lte":
            df = df[s <= v]
        elif f.op == "contains":
            df = df[s.astype(str).str.contains(f.values[0], case=False, na=False, regex=False)]
    return df


def _num(v: Any) -> Any:
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return round(float(v), 4)
    return v


def _label(v: Any, grain: str | None = None) -> str:
    if isinstance(v, pd.Timestamp):
        if grain == "year":
            return v.strftime("%Y")
        if grain == "quarter":
            return f"{v.year}-Q{(v.month - 1) // 3 + 1}"
        if grain == "month":
            return v.strftime("%Y-%m")
        return v.strftime("%Y-%m-%d")
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "(blank)"
    return str(v)


def _aggregate(grouped, y: str | None, agg: str):
    if agg == "count" or y is None:
        return grouped.size()
    col = grouped[y]
    if agg == "count_distinct":
        return col.nunique()
    return getattr(col, agg)()


def _measure_check(df: pd.DataFrame, y: str | None, agg: str) -> None:
    if agg in ("count", "count_distinct"):
        return
    if y is None:
        raise ChartError(f"'{agg}' needs a measure column (y)")
    if not pd.api.types.is_numeric_dtype(df[y]):
        raise ChartError(f"Column '{y}' is not numeric, so it can't be summed or averaged")


def _x_key(df: pd.DataFrame, chart: ChartSpec) -> pd.Series:
    x = df[chart.x]
    if pd.api.types.is_datetime64_any_dtype(x):
        grain = chart.time_grain or "month"
        return x.dt.to_period(PERIOD[grain]).dt.start_time.rename(chart.x)
    return x.astype(str).where(x.notna(), "(blank)").rename(chart.x)


def _categorical(df: pd.DataFrame, chart: ChartSpec) -> Dict[str, Any]:
    if not chart.x:
        raise ChartError(f"A {chart.type} chart needs an x column")
    _require(df, chart.x, chart.y, chart.series)
    _measure_check(df, chart.y, chart.agg)
    is_time = pd.api.types.is_datetime64_any_dtype(df[chart.x])
    xkey = _x_key(df, chart)

    if chart.series and chart.type != "pie":
        skey = df[chart.series].astype(str).where(df[chart.series].notna(), "(blank)")
        top_series = (
            _aggregate(df.groupby(skey), chart.y, chart.agg).sort_values(ascending=False).head(8).index
        )
        mask = skey.isin(top_series)
        table = _aggregate(df[mask].groupby([xkey[mask], skey[mask]]), chart.y, chart.agg).unstack(fill_value=0)
        keys = [str(k) for k in table.columns]
        totals = table.sum(axis=1)
    else:
        series = _aggregate(df.groupby(xkey), chart.y, chart.agg)
        key = chart.y if chart.y and chart.agg != "count" else "count"
        table = series.to_frame(name=key)
        keys = [key]
        totals = series

    order = chart.sort or ("x_asc" if is_time else "value_desc")
    if order == "value_desc":
        table = table.loc[totals.sort_values(ascending=False).index]
    elif order == "value_asc":
        table = table.loc[totals.sort_values(ascending=True).index]
    elif order == "x_desc":
        table = table.sort_index(ascending=False)
    else:
        table = table.sort_index()

    limit = chart.limit or (None if is_time else MAX_CATEGORIES)
    truncated = False
    if limit and len(table) > limit:
        table = table.head(limit)
        truncated = True

    rows = []
    for idx, rec in table.iterrows():
        row = {"x": _label(idx, chart.time_grain or ("month" if is_time else None))}
        row.update({str(k): _num(v) for k, v in rec.items()})
        rows.append(row)
    return {"keys": keys, "rows": rows, "truncated": truncated}


def _kpi(df: pd.DataFrame, chart: ChartSpec) -> Dict[str, Any]:
    _require(df, chart.y)
    _measure_check(df, chart.y, chart.agg)
    if chart.agg == "count" or not chart.y:
        value = len(df)
    elif chart.agg == "count_distinct":
        value = df[chart.y].nunique()
    else:
        value = getattr(df[chart.y], chart.agg)()
    return {"value": _num(value), "label": f"{chart.agg} of {chart.y}" if chart.y else "rows"}


def _nice_edges(lo: float, hi: float, target: int, integer: bool = False) -> np.ndarray:
    if hi <= lo:
        return np.array([lo - 0.5, hi + 0.5])
    raw = (hi - lo) / target
    mag = 10 ** np.floor(np.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    if integer:
        step = max(1.0, round(step))
        if step == 1:
            return np.arange(lo - 0.5, hi + 1.5, 1.0)
    start = np.floor(lo / step) * step
    return np.arange(start, hi + step, step)


def _fmt_edge(v: float) -> str:
    return f"{v:,.0f}" if float(v).is_integer() else f"{v:,.4g}"


def _histogram(df: pd.DataFrame, chart: ChartSpec) -> Dict[str, Any]:
    col = chart.x or chart.y
    if not col:
        raise ChartError("A histogram needs a numeric column")
    _require(df, col)
    s = df[col].dropna()
    if not pd.api.types.is_numeric_dtype(s):
        raise ChartError(f"Column '{col}' is not numeric")
    if s.empty:
        return {"keys": ["count"], "rows": []}
    target = min(chart.limit or 20, max(5, int(np.sqrt(len(s)))))
    edges = _nice_edges(float(s.min()), float(s.max()), target, bool((s % 1 == 0).all()))
    counts, edges = np.histogram(s, bins=edges)
    unit_bins = len(edges) > 1 and edges[1] - edges[0] == 1 and edges[0] % 1 == 0.5
    rows = [
        {"x": _fmt_edge(edges[i] + 0.5) if unit_bins else f"{_fmt_edge(edges[i])}–{_fmt_edge(edges[i + 1])}",
         "count": int(c)}
        for i, c in enumerate(counts)
    ]
    return {"keys": ["count"], "rows": rows}


def _scatter(df: pd.DataFrame, chart: ChartSpec) -> Dict[str, Any]:
    if not chart.x or not chart.y:
        raise ChartError("A scatter chart needs numeric x and y columns")
    _require(df, chart.x, chart.y, chart.series)
    for c in (chart.x, chart.y):
        if not pd.api.types.is_numeric_dtype(df[c]):
            raise ChartError(f"Column '{c}' is not numeric")
    cols = [chart.x, chart.y] + ([chart.series] if chart.series else [])
    sub = df[cols].dropna(subset=[chart.x, chart.y])
    if len(sub) > MAX_SCATTER_POINTS:
        sub = sub.sample(MAX_SCATTER_POINTS, random_state=0)
    points = [
        {"x": _num(r[chart.x]), "y": _num(r[chart.y]),
         "series": str(r[chart.series]) if chart.series else "all"}
        for _, r in sub.iterrows()
    ]
    keys = sorted({p["series"] for p in points})[:8]
    points = [p for p in points if p["series"] in keys]
    return {"keys": keys, "points": points}


def _table(df: pd.DataFrame, chart: ChartSpec) -> Dict[str, Any]:
    cols = chart.columns or [c for c in (chart.x, chart.y, chart.series) if c] or list(df.columns)
    _require(df, *cols)
    sub = df[cols]
    if chart.y and chart.sort in ("value_desc", "value_asc") and chart.y in sub:
        sub = sub.sort_values(chart.y, ascending=chart.sort == "value_asc")
    sub = sub.head(min(chart.limit or 50, MAX_TABLE_ROWS))
    rows = [{c: _num(v) if not isinstance(v, pd.Timestamp) else _label(v) for c, v in r.items()}
            for r in sub.to_dict(orient="records")]
    return {"columns": cols, "rows": rows}


def _color_slots(df: pd.DataFrame, column: str, names: List[str]) -> Dict[str, int]:
    # Slot by frequency in the full column, so a category keeps its color in
    # every chart and across reloads, whatever the chart's own sort or filters.
    s = df[column]
    order = s.astype(str).where(s.notna(), "(blank)").value_counts().index
    rank = {str(v): i for i, v in enumerate(order)}
    return {n: rank.get(n, i) % 8 for i, n in enumerate(names)}


def compute_chart(df: pd.DataFrame, chart: ChartSpec) -> Dict[str, Any]:
    full = df
    df = apply_filters(df, chart.filters)
    if chart.type == "kpi":
        return _kpi(df, chart)
    if chart.type == "histogram":
        return _histogram(df, chart)
    if chart.type == "table":
        return _table(df, chart)
    if chart.type in ("bar", "line", "area", "pie"):
        out = _categorical(df, chart)
    elif chart.type == "scatter":
        out = _scatter(df, chart)
    else:
        raise ChartError(f"Unsupported chart type {chart.type}")

    if chart.type == "pie" and chart.x:
        out["slots"] = _color_slots(full, chart.x, [r["x"] for r in out["rows"]])
    elif chart.series and len(out["keys"]) > 1:
        out["slots"] = _color_slots(full, chart.series, out["keys"])
    return out


def render_dashboard(df: pd.DataFrame, charts: List[ChartSpec]) -> List[Dict[str, Any]]:
    out = []
    for chart in charts:
        try:
            out.append({"spec": chart.model_dump(), "data": compute_chart(df, chart), "error": None})
        except ChartError as exc:
            out.append({"spec": chart.model_dump(), "data": None, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            out.append({"spec": chart.model_dump(), "data": None, "error": f"Could not compute chart: {exc}"})
    return out
