import pytest

from app.engine import ChartError, compute_chart, render_dashboard
from app.profiling import read_table
from app.spec import ChartSpec, Filter


@pytest.fixture
def df(sample_bytes):
    return read_table("sales.csv", sample_bytes)


def test_kpi_sum(df):
    out = compute_chart(df, ChartSpec(id="k", type="kpi", title="Rev", y="revenue", agg="sum"))
    assert out["value"] == pytest.approx(df["revenue"].sum(), rel=1e-6)


def test_kpi_count_without_measure(df):
    out = compute_chart(df, ChartSpec(id="k", type="kpi", title="Rows", agg="count"))
    assert out["value"] == len(df)


def test_bar_sorted_desc_and_limited(df):
    out = compute_chart(df, ChartSpec(id="b", type="bar", title="t", x="category", y="revenue", limit=2))
    assert len(out["rows"]) == 2
    assert out["truncated"] is True
    assert out["rows"][0]["revenue"] >= out["rows"][1]["revenue"]


def test_line_by_month_with_series(df):
    out = compute_chart(df, ChartSpec(id="l", type="line", title="t", x="order_date", y="profit",
                                      series="region", time_grain="month"))
    assert set(out["keys"]) == {"North", "South", "East", "West"}
    labels = [r["x"] for r in out["rows"]]
    assert labels == sorted(labels)
    assert labels[0] == "2025-01"


def test_filters(df):
    chart = ChartSpec(id="k", type="kpi", title="t", agg="count",
                      filters=[Filter(column="region", op="eq", values=["North"]),
                               Filter(column="revenue", op="gt", values=["500"])])
    expected = ((df["region"] == "North") & (df["revenue"] > 500)).sum()
    assert compute_chart(df, chart)["value"] == expected


def test_histogram_and_scatter(df):
    hist = compute_chart(df, ChartSpec(id="h", type="histogram", title="t", x="revenue", limit=10))
    assert sum(r["count"] for r in hist["rows"]) == df["revenue"].notna().sum()
    sc = compute_chart(df, ChartSpec(id="s", type="scatter", title="t", x="revenue", y="profit", series="channel"))
    assert len(sc["points"]) == len(df)
    assert set(sc["keys"]) == {"Online", "Retail", "Partner"}


def test_bad_column_reports_error_without_breaking_others(df):
    charts = [
        ChartSpec(id="ok", type="kpi", title="t", agg="count"),
        ChartSpec(id="bad", type="bar", title="t", x="nope", y="revenue"),
        ChartSpec(id="text", type="bar", title="t", x="region", y="channel", agg="sum"),
    ]
    out = render_dashboard(df, charts)
    assert out[0]["error"] is None
    assert "Unknown column" in out[1]["error"]
    assert "not numeric" in out[2]["error"]


def test_measure_required_for_sum(df):
    with pytest.raises(ChartError):
        compute_chart(df, ChartSpec(id="b", type="bar", title="t", x="region", agg="sum"))


def test_histogram_integer_bins_are_labelled_by_value(df):
    rows = compute_chart(df, ChartSpec(id="h", type="histogram", title="t", x="customer_rating"))["rows"]
    assert [r["x"] for r in rows] == ["1", "2", "3", "4", "5"]
    assert rows[0]["count"] == (df["customer_rating"] == 1).sum()
