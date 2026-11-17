"""Dashboard spec models. Field descriptions are sent to the model as the output schema."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

ChartType = Literal["kpi", "bar", "line", "area", "pie", "scatter", "histogram", "table"]
Aggregation = Literal["sum", "mean", "median", "min", "max", "count", "count_distinct"]
TimeGrain = Literal["day", "week", "month", "quarter", "year"]
SortOrder = Literal["value_desc", "value_asc", "x_asc", "x_desc"]
FilterOp = Literal["eq", "neq", "in", "not_in", "gt", "gte", "lt", "lte", "contains"]
Width = Literal["third", "half", "full"]


class Filter(BaseModel):
    # single-value ops read values[0]; in/not_in use the full list
    column: str
    op: FilterOp
    values: List[str]


class ChartSpec(BaseModel):
    id: str = Field(description="Short unique slug, e.g. 'revenue-by-region'.")
    type: ChartType
    title: str
    x: Optional[str] = Field(
        default=None,
        description="Dimension column (category or date). For scatter: numeric x. For histogram: the numeric column to bin. Unused for kpi.",
    )
    y: Optional[str] = Field(
        default=None,
        description="Measure column to aggregate. May be null when agg is 'count'.",
    )
    agg: Aggregation = "sum"
    series: Optional[str] = Field(
        default=None,
        description="Optional second dimension that splits bar/line/area charts into several series.",
    )
    time_grain: Optional[TimeGrain] = Field(
        default=None, description="Bucket size when x is a date column."
    )
    sort: Optional[SortOrder] = None
    limit: Optional[int] = Field(
        default=None, description="Keep the top N categories (bar/pie) or rows (table)."
    )
    filters: List[Filter] = Field(default_factory=list)
    columns: List[str] = Field(
        default_factory=list, description="Columns to show, for table charts only."
    )
    width: Width = "half"
    rationale: str = Field(
        default="", description="One sentence on why this chart is useful for this data."
    )


class DashboardSpec(BaseModel):
    title: str
    description: str = ""
    charts: List[ChartSpec]


class PlannerResult(BaseModel):
    reply: str = Field(
        description="Short, plain-English message to the user about what was built or changed."
    )
    dashboard: DashboardSpec
