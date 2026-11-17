"""File loading, type inference and column profiling."""

from __future__ import annotations

import io
import re
import warnings
from typing import Any, Dict, List

import pandas as pd

MEASURE_HINTS = (
    "revenue", "sales", "amount", "price", "profit", "cost", "total", "value",
    "quantity", "qty", "units", "spend", "income", "margin", "score", "count",
    "duration", "balance", "fee", "budget",
)
ID_HINT = re.compile(r"(^id$|_id$|^id_|uuid|guid|\bid\b)", re.IGNORECASE)
DATE_HINT = re.compile(r"(date|time|day|month|year|created|updated|_at$|timestamp|period)", re.IGNORECASE)


class UnsupportedFile(ValueError):
    pass


def read_table(filename: str, content: bytes) -> pd.DataFrame:
    name = filename.lower()
    if name.endswith((".csv", ".txt")):
        df = pd.read_csv(io.BytesIO(content), sep=None, engine="python")
    elif name.endswith(".tsv"):
        df = pd.read_csv(io.BytesIO(content), sep="\t")
    elif name.endswith((".xlsx", ".xlsm", ".xls")):
        df = pd.read_excel(io.BytesIO(content))
    elif name.endswith(".json"):
        df = pd.read_json(io.BytesIO(content))
    else:
        raise UnsupportedFile("Upload a CSV, TSV, Excel or JSON file.")
    if df.empty:
        raise UnsupportedFile("The file has no rows.")
    df.columns = [str(c).strip() or f"column_{i}" for i, c in enumerate(df.columns)]
    return normalise_types(df)


def _looks_like_dates(sample: pd.Series) -> bool:
    text = sample.astype(str)
    return bool(text.str.contains(r"\d{1,4}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|[A-Za-z]{3,9}\s+\d{4}", regex=True).mean() > 0.8)


def normalise_types(df: pd.DataFrame) -> pd.DataFrame:
    """Convert text columns that are really numbers or dates."""
    df = df.copy()
    for col in df.columns:
        s = df[col]
        if not (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)):
            continue
        non_null = s.dropna()
        if non_null.empty:
            continue
        cleaned = non_null.astype(str).str.replace(r"[,$€£%\s]", "", regex=True)
        as_num = pd.to_numeric(cleaned, errors="coerce")
        if as_num.notna().mean() >= 0.95:
            df[col] = pd.to_numeric(
                s.astype(str).str.replace(r"[,$€£%\s]", "", regex=True), errors="coerce"
            ).where(s.notna())
            continue
        if _looks_like_dates(non_null.head(200)) or DATE_HINT.search(col):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                as_dt = pd.to_datetime(non_null, errors="coerce", format="mixed")
            if as_dt.notna().mean() >= 0.9:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    df[col] = pd.to_datetime(s, errors="coerce", format="mixed")
    return df


def column_kind(name: str, s: pd.Series) -> str:
    n = len(s)
    unique = s.nunique(dropna=True)
    if pd.api.types.is_bool_dtype(s):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "datetime"
    if pd.api.types.is_numeric_dtype(s):
        if ID_HINT.search(name) and unique >= 0.9 * n:
            return "id"
        return "numeric"
    if n and unique >= 0.9 * n and unique > 20:
        return "id" if ID_HINT.search(name) or s.astype(str).str.len().mean() < 40 else "text"
    if unique > 200 and s.astype(str).str.len().mean() > 40:
        return "text"
    return "categorical"


def _jsonable(v: Any) -> Any:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if hasattr(v, "item"):
        return v.item()
    return v


def profile_frame(df: pd.DataFrame) -> Dict[str, Any]:
    columns: List[Dict[str, Any]] = []
    for col in df.columns:
        s = df[col]
        kind = column_kind(col, s)
        info: Dict[str, Any] = {
            "name": col,
            "kind": kind,
            "null_pct": round(float(s.isna().mean()) * 100, 1),
            "unique": int(s.nunique(dropna=True)),
        }
        non_null = s.dropna()
        if kind == "numeric" and not non_null.empty:
            info.update(
                min=_jsonable(non_null.min()),
                max=_jsonable(non_null.max()),
                mean=round(float(non_null.mean()), 4),
                is_integer=bool(pd.api.types.is_integer_dtype(non_null) or (non_null % 1 == 0).all()),
                looks_like_measure=any(h in col.lower() for h in MEASURE_HINTS),
            )
        elif kind == "datetime" and not non_null.empty:
            info.update(min=_jsonable(non_null.min()), max=_jsonable(non_null.max()),
                        span_days=int((non_null.max() - non_null.min()).days))
        elif kind in ("categorical", "boolean"):
            top = non_null.astype(str).value_counts().head(8)
            info["top_values"] = [{"value": k, "count": int(v)} for k, v in top.items()]
        info["samples"] = [_jsonable(v) for v in non_null.head(3).tolist()]
        columns.append(info)
    return {"row_count": int(len(df)), "column_count": int(df.shape[1]), "columns": columns}
