"""Candidate charts the user can add to a dashboard, ranked against their stated goal."""

from __future__ import annotations

import re
from itertools import combinations
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .planner import ADDITIVE_HINTS, _default_agg, _humanize, _is_continuous
from .spec import ChartSpec

MAX_SUGGESTIONS = 12


def signature(c: ChartSpec) -> Tuple:
    return (c.type, c.x, c.y, c.series, c.agg if c.y else "count")


def _slug(*parts: Optional[str]) -> str:
    return "-".join(re.sub(r"[^a-z0-9]+", "-", p.lower()).strip("-") for p in parts if p)


def _measure_title(col: Dict[str, Any], agg: str) -> str:
    name = _humanize(col["name"])
    return name if agg == "sum" else f"Average {name.lower()}"


def _words(name: str) -> str:
    return name.replace("_", " ")


def _candidates(profile: Dict[str, Any]) -> Iterable[Tuple[float, ChartSpec]]:
    cols = profile["columns"]
    numeric = [c for c in cols if c["kind"] == "numeric" and c["unique"] > 1]
    measures = sorted(numeric, key=lambda c: (_default_agg(c) != "sum",
                                              next((i for i, h in enumerate(ADDITIVE_HINTS) if h in c["name"].lower()), 99)))
    dates = [c for c in cols if c["kind"] == "datetime" and c["unique"] > 1]
    cats = sorted((c for c in cols if c["kind"] in ("categorical", "boolean") and 2 <= c["unique"] <= 50),
                  key=lambda c: (c["null_pct"], c["unique"]))
    small = [c for c in cats if c["unique"] <= 8]
    ids = [c for c in cols if c["kind"] == "id"]

    for mi, m in enumerate(measures[:4]):
        agg = _default_agg(m)
        mh = _measure_title(m, agg)
        for ci, c in enumerate(cats[:5]):
            yield 10 - mi - ci, ChartSpec(
                id=_slug(m["name"], "by", c["name"]), type="bar", x=c["name"], y=m["name"], agg=agg,
                sort="value_desc", limit=15, title=f"{mh} by {_words(c['name'])}",
                rationale=f"Compares {m['name']} across {c['name']} groups.",
            )
        for d in dates[:1]:
            span = d.get("span_days", 0)
            grain = "day" if span <= 92 else "week" if span <= 270 else "month" if span <= 1100 else "quarter"
            yield 9 - mi, ChartSpec(
                id=_slug(m["name"], "over", d["name"]), type="line", x=d["name"], y=m["name"], agg=agg,
                time_grain=grain, width="full", title=f"{mh} over time",
                rationale=f"Trend of {m['name']}.",
            )
            for c in small[:3]:
                yield 8 - mi, ChartSpec(
                    id=_slug(m["name"], "over-time-by", c["name"]), type="line", x=d["name"], y=m["name"],
                    agg=agg, series=c["name"], time_grain=grain, width="full",
                    title=f"{mh} over time by {_words(c['name'])}",
                    rationale=f"Whether the {m['name']} trend differs between {c['name']} groups.",
                )
        if agg == "sum":
            for c in small[:2]:
                yield 6 - mi, ChartSpec(
                    id=_slug("share", m["name"], c["name"]), type="pie", x=c["name"], y=m["name"], agg="sum",
                    title=f"Share of {_words(m['name'])} by {_words(c['name'])}",
                    rationale=f"Part-to-whole split of {m['name']}.",
                )
        for a, b in combinations(cats[:4], 2):
            inner = b if b["unique"] <= 8 else a if a["unique"] <= 8 else None
            outer = a if inner is b else b
            if inner is None:
                continue
            yield 7 - mi, ChartSpec(
                id=_slug(m["name"], "by", outer["name"], inner["name"]), type="bar", x=outer["name"],
                y=m["name"], agg=agg, series=inner["name"], sort="value_desc", limit=12,
                title=f"{mh} by {_words(outer['name'])} and {_words(inner['name'])}",
                rationale=f"Compares {m['name']} across two dimensions at once.",
            )
        if _is_continuous(m):
            yield 4 - mi, ChartSpec(
                id=_slug("dist", m["name"]), type="histogram", x=m["name"], limit=20,
                title=f"Distribution of {_words(m['name'])}", rationale="Typical values and outliers.",
            )
        yield 5 - mi, ChartSpec(
            id=_slug("kpi", agg, m["name"]), type="kpi", y=m["name"], agg=agg, width="third",
            title=f"Total {_words(m['name'])}" if agg == "sum" else mh, rationale=f"Headline {m['name']}.",
        )

    for ci, c in enumerate(cats[:4]):
        yield 5 - ci, ChartSpec(
            id=_slug("records-by", c["name"]), type="bar", x=c["name"], agg="count", sort="value_desc", limit=15,
            title=f"Records by {_words(c['name'])}", rationale=f"How rows split across {c['name']}.",
        )

    continuous = [m for m in measures if _is_continuous(m)]
    for a, b in combinations(continuous[:4], 2):
        yield 5, ChartSpec(
            id=_slug(b["name"], "vs", a["name"]), type="scatter", x=a["name"], y=b["name"],
            series=small[0]["name"] if small and small[0]["unique"] <= 3 else None,
            title=f"{_humanize(b['name'])} vs {_words(a['name'])}",
            rationale=f"Whether {a['name']} and {b['name']} move together.",
        )

    row_count = profile["row_count"]
    for c in ids:
        if c["unique"] < row_count:
            yield 6, ChartSpec(
                id=_slug("distinct", c["name"]), type="kpi", y=c["name"], agg="count_distinct", width="third",
                title=f"Unique {_humanize(c['name']).lower()}", rationale=f"Distinct values of {c['name']}.",
            )


def _stem(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def _tokens(text: str) -> set:
    return {_stem(w) for w in re.findall(r"[a-z0-9]+", text.lower())}


def _relevance(chart: ChartSpec, text: str) -> float:
    if not text:
        return 0.0
    words = _tokens(text)
    score = 0.0
    for col in (chart.x, chart.y, chart.series):
        if col and _tokens(col) <= words:
            score += 6
    if chart.type in ("line", "area") and re.search(r"trend|over time|month|week|daily|growth|season", text):
        score += 4
    if chart.series and re.search(r"compar|versus|\bvs\b|split|breakdown|break down|each", text):
        score += 3
    if chart.type == "scatter" and re.search(r"correlat|relationship|driv|impact|affect", text):
        score += 4
    if chart.type == "pie" and re.search(r"share|mix|proportion|percent", text):
        score += 3
    if chart.type == "histogram" and re.search(r"distribut|outlier|spread|range", text):
        score += 3
    return score


def suggest(
    profile: Dict[str, Any],
    existing: List[ChartSpec],
    requirements: str = "",
    preferred: Optional[List[ChartSpec]] = None,
    limit: int = MAX_SUGGESTIONS,
) -> List[ChartSpec]:
    """Return charts not already on the dashboard, most relevant first.

    `preferred` are suggestions from the model, which already account for the
    user's goal; they go first. The rule-based candidates fill the rest.
    """
    taken = {signature(c) for c in existing}
    used_ids = {c.id for c in existing}
    text = requirements.lower()
    out: List[ChartSpec] = []

    def add(c: ChartSpec) -> None:
        sig = signature(c)
        if sig in taken:
            return
        taken.add(sig)
        if c.id in used_ids:
            c = c.model_copy(update={"id": f"{c.id}-{len(used_ids)}"})
        used_ids.add(c.id)
        out.append(c)

    for c in preferred or []:
        add(c)

    # Greedy pick with a penalty for repeating a chart type, so the list mixes
    # breakdowns, trends and relationships instead of twelve bar charts.
    pool = [(base + _relevance(c, text), c) for base, c in _candidates(profile)]
    per_type: Dict[str, int] = {}
    while pool and len(out) < limit:
        best = max(range(len(pool)), key=lambda i: pool[i][0] - 2.5 * per_type.get(pool[i][1].type, 0))
        _, c = pool.pop(best)
        before = len(out)
        add(c)
        if len(out) > before:
            per_type[c.type] = per_type.get(c.type, 0) + 1
    return out[:limit]
