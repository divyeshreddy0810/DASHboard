from app.planner import HeuristicPlanner
from app.profiling import profile_frame, read_table
from app.spec import ChartSpec
from app.suggestions import signature, suggest


def _setup(sample_bytes):
    profile = profile_frame(read_table("sales.csv", sample_bytes))
    return profile, HeuristicPlanner().create(profile, "sales").dashboard


def test_suggestions_skip_charts_already_on_dashboard(sample_bytes):
    profile, dash = _setup(sample_bytes)
    out = suggest(profile, dash.charts)
    existing = {signature(c) for c in dash.charts}
    assert out
    assert not existing & {signature(c) for c in out}
    assert len({c.id for c in out}) == len(out)


def test_suggestions_follow_the_goal(sample_bytes):
    profile, dash = _setup(sample_bytes)
    out = suggest(profile, dash.charts, "compare profit across categories over time")
    top = out[:4]
    assert all("profit" in (c.y or "") or c.series == "category" or c.x == "category" for c in top)
    assert any(c.type == "line" for c in top)


def test_model_suggestions_come_first_and_are_deduped(sample_bytes):
    profile, dash = _setup(sample_bytes)
    preferred = [
        ChartSpec(id="margin", type="bar", title="Avg margin", x="category", y="profit", agg="mean"),
        dash.charts[1],
    ]
    out = suggest(profile, dash.charts, "", preferred)
    assert out[0].id == "margin"
    assert signature(dash.charts[1]) not in {signature(c) for c in out}
