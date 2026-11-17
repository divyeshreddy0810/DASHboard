"""Dashboard planners: Claude (structured output) and a rule-based fallback."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .spec import ChartSpec, DashboardSpec, PlannerResult

MODEL = os.environ.get("DASHBOARD_MODEL", "claude-opus-5-5")

SYSTEM_PROMPT = """You design analytics dashboards. You receive a profile of a dataset (column names, \
types, ranges, cardinality, sample values, but not the rows) and, for edits, the current dashboard \
and the user's request. You return a dashboard spec that a rendering engine computes from the data.

How the engine reads a chart:
- kpi: one number. Set y and agg (or agg "count" with y null for a row count).
- bar / pie: x is a categorical column, y is a numeric measure aggregated with agg. Optional series \
splits bars by a second category (not for pie). Use pie only for 2 to 6 categories that are parts of a whole.
- line / area: x is a datetime column bucketed by time_grain, y is a measure. Optional series.
- histogram: x is the numeric column to bin; limit is the bin count.
- scatter: x and y are numeric columns; optional series colours points by a category.
- table: columns lists what to show; sort and limit pick the rows.
- filters narrow the rows for one chart. values are strings; comparison ops use values[0].
- width is the share of the row the chart takes: third, half or full.

Rules:
- Use only column names that appear in the profile, spelled exactly.
- Never aggregate an id column or a text column as a measure; count rows instead.
- Lead with 2 to 4 KPIs, then the charts that answer the most obvious business questions \
(trend over time, breakdown by the main categories, distribution, relationships). 6 to 10 charts total.
- Give each chart a short, specific title and a one-sentence rationale.
- When editing, change only what the user asked for and keep every other chart's id and settings. \
If the request can't be done with this data, keep the dashboard as it is and say why in reply.
- suggestions are extra charts the user can drag onto the dashboard. Make them comparisons that \
answer the user's stated goal and earlier requests: breakdowns by other dimensions, trends split by \
category, two-dimension comparisons, relationships between measures. Don't repeat charts already on \
the dashboard.
- reply is one to three plain sentences addressed to the user."""


class PlannerUnavailable(RuntimeError):
    pass


def _profile_for_prompt(profile: Dict[str, Any]) -> str:
    return json.dumps(profile, default=str, separators=(",", ":"))


class ClaudePlanner:
    name = "claude"

    def __init__(self, client: Any = None, model: str = MODEL):
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        self.client = client
        self.model = model

    def _call(self, user_content: str) -> PlannerResult:
        import anthropic

        try:
            response = self.client.beta.messages.parse(
                model=self.model,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
                output_format=PlannerResult,
                output_config={"effort": "medium"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AuthenticationError as exc:
            raise PlannerUnavailable("The Anthropic API key was rejected.") from exc
        except anthropic.RateLimitError as exc:
            raise PlannerUnavailable("The Anthropic API is rate limiting requests. Try again shortly.") from exc
        except anthropic.APIStatusError as exc:
            raise PlannerUnavailable(f"The Anthropic API returned an error ({exc.status_code}).") from exc
        except anthropic.APIConnectionError as exc:
            raise PlannerUnavailable("Could not reach the Anthropic API.") from exc

        if response.stop_reason == "refusal":
            raise PlannerUnavailable("The model declined this request.")
        if response.stop_reason == "max_tokens" or response.parsed_output is None:
            raise PlannerUnavailable("The model's answer was cut off. Try a smaller request.")
        return response.parsed_output

    def create(self, profile: Dict[str, Any], dataset_name: str, goal: Optional[str] = None) -> PlannerResult:
        content = (
            f"Dataset: {dataset_name}\n"
            f"Profile:\n{_profile_for_prompt(profile)}\n\n"
            + (f"The user says what they want to learn: {goal}\n\n" if goal else "")
            + "Design the first version of this dashboard."
        )
        return self._call(content)

    def edit(
        self,
        profile: Dict[str, Any],
        dataset_name: str,
        current: DashboardSpec,
        history: List[Dict[str, str]],
        request: str,
    ) -> PlannerResult:
        recent = history[-10:]
        convo = "\n".join(f"{m['role']}: {m['content']}" for m in recent) or "(none)"
        content = (
            f"Dataset: {dataset_name}\n"
            f"Profile:\n{_profile_for_prompt(profile)}\n\n"
            f"Current dashboard:\n{current.model_dump_json()}\n\n"
            f"Earlier conversation:\n{convo}\n\n"
            f"New request from the user: {request}\n\n"
            "Return the full updated dashboard."
        )
        return self._call(content)


ADDITIVE_HINTS = ("revenue", "sales", "amount", "profit", "income", "spend", "cost", "total",
                  "value", "quantity", "qty", "units", "volume", "fee", "budget", "count")
AVERAGE_HINTS = ("price", "rate", "rating", "score", "pct", "percent", "ratio", "avg",
                 "average", "age", "margin", "duration", "temperature")


def _humanize(name: str) -> str:
    text = name.replace("_", " ").replace("-", " ").strip()
    return text[:1].upper() + text[1:]


def _hint_rank(name: str, hints) -> int:
    lower = name.lower()
    return next((i for i, h in enumerate(hints) if h in lower), len(hints))


def _default_agg(col: Dict[str, Any]) -> str:
    name = col["name"]
    if _hint_rank(name, AVERAGE_HINTS) < len(AVERAGE_HINTS):
        return "mean"
    return "sum" if _hint_rank(name, ADDITIVE_HINTS) < len(ADDITIVE_HINTS) else "mean"


def _is_continuous(col: Dict[str, Any]) -> bool:
    return not col.get("is_integer") or col["unique"] > 30


class HeuristicPlanner:
    name = "heuristic"

    def create(self, profile: Dict[str, Any], dataset_name: str, goal: Optional[str] = None) -> PlannerResult:
        cols = profile["columns"]
        numeric = [c for c in cols if c["kind"] == "numeric" and c["unique"] > 1]
        additive = sorted(
            (c for c in numeric if _default_agg(c) == "sum"),
            key=lambda c: (_hint_rank(c["name"], ADDITIVE_HINTS), c["null_pct"]),
        )
        averaged = [c for c in numeric if _default_agg(c) == "mean"]
        dates = [c for c in cols if c["kind"] == "datetime" and c["unique"] > 1]
        cats = [c for c in cols if c["kind"] in ("categorical", "boolean") and 2 <= c["unique"] <= 50]
        cats.sort(key=lambda c: (c["null_pct"], c["unique"]))

        main = additive[0] if additive else None
        measure = _humanize(main["name"]) if main else "Records"
        y = main["name"] if main else None
        agg = "sum" if main else "count"

        charts: List[ChartSpec] = [
            ChartSpec(id="records", type="kpi", title="Records", agg="count", width="third",
                      rationale="How much data the dashboard covers.")
        ]
        for m in (additive[:2] + averaged[:1])[:2]:
            a = _default_agg(m)
            charts.append(ChartSpec(
                id=f"kpi-{m['name']}", type="kpi", width="third", y=m["name"], agg=a,
                title=f"{'Total' if a == 'sum' else 'Average'} {_humanize(m['name']).lower()}",
                rationale=f"Headline figure for {m['name']}.",
            ))

        if dates:
            d = dates[0]
            span = d.get("span_days", 0)
            grain = "day" if span <= 92 else "week" if span <= 270 else "month" if span <= 1100 else "quarter"
            charts.append(ChartSpec(
                id="trend", type="line", width="full", title=f"{measure} over time",
                x=d["name"], y=y, agg=agg, time_grain=grain,
                rationale="How the main measure moves over time.",
            ))

        for c in cats[:2]:
            charts.append(ChartSpec(
                id=f"by-{c['name']}", type="bar", width="half",
                title=f"{measure} by {_humanize(c['name']).lower()}",
                x=c["name"], y=y, agg=agg, sort="value_desc", limit=15,
                rationale=f"Compares {c['name']} groups.",
            ))

        small = [c for c in cats if c["unique"] <= 6]
        if small:
            c = small[0]
            charts.append(ChartSpec(
                id=f"share-{c['name']}", type="pie", width="half",
                title=f"Share of {measure.lower()} by {_humanize(c['name']).lower()}",
                x=c["name"], y=y, agg=agg, rationale=f"Part-to-whole split across {c['name']}.",
            ))

        continuous = [c for c in additive + averaged if _is_continuous(c)]
        if continuous:
            h = continuous[0]
            charts.append(ChartSpec(
                id=f"dist-{h['name']}", type="histogram", width="half",
                title=f"Distribution of {_humanize(h['name']).lower()}", x=h["name"], limit=20,
                rationale="Typical values and outliers.",
            ))
        if len(continuous) >= 2:
            a, b = continuous[0], continuous[1]
            charts.append(ChartSpec(
                id="relationship", type="scatter", width="half",
                title=f"{_humanize(b['name'])} vs {_humanize(a['name']).lower()}",
                x=a["name"], y=b["name"], series=small[0]["name"] if small and small[0]["unique"] <= 3 else None,
                rationale="Whether the two measures move together.",
            ))

        charts.append(ChartSpec(
            id="preview", type="table", width="full", title="Data preview",
            columns=[c["name"] for c in cols[:8]], limit=20, rationale="The underlying rows.",
        ))
        spec = DashboardSpec(
            title=f"{_humanize(dataset_name)} overview",
            description=f"{profile['row_count']:,} rows, {profile['column_count']} columns.",
            charts=charts,
        )
        return PlannerResult(
            reply="Here's a first dashboard built from the column types. "
                  "Set ANTHROPIC_API_KEY to let Claude design it and to edit it by chat.",
            dashboard=spec,
        )

    def edit(self, profile, dataset_name, current, history, request) -> PlannerResult:
        raise PlannerUnavailable(
            "Editing by chat needs Claude. Set ANTHROPIC_API_KEY on the backend and restart it."
        )


def default_planner():
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return ClaudePlanner()
    return HeuristicPlanner()
