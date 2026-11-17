from app.planner import HeuristicPlanner
from app.profiling import profile_frame, read_table


def test_heuristic_prefers_additive_measures(sample_bytes):
    profile = profile_frame(read_table("sales.csv", sample_bytes))
    spec = HeuristicPlanner().create(profile, "sales").dashboard
    by_id = {c.id: c for c in spec.charts}

    assert spec.title == "Sales overview"
    assert by_id["kpi-revenue"].agg == "sum"
    assert by_id["trend"].y == "revenue" and by_id["trend"].x == "order_date"
    assert all(c.y != "unit_price" or c.agg == "mean" for c in spec.charts)
    assert by_id["relationship"].x == "revenue"
