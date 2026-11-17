import pandas as pd

from app.profiling import normalise_types, profile_frame, read_table


def test_read_and_profile_sample(sample_bytes):
    df = read_table("sales.csv", sample_bytes)
    profile = profile_frame(df)
    kinds = {c["name"]: c["kind"] for c in profile["columns"]}

    assert profile["row_count"] == 1200
    assert kinds["order_date"] == "datetime"
    assert kinds["region"] == "categorical"
    assert kinds["revenue"] == "numeric"
    assert kinds["order_id"] == "id"


def test_normalise_currency_and_dates():
    df = pd.DataFrame({
        "amount": ["$1,200.50", "$30", None],
        "when": ["2024-01-05", "2024-02-10", "2024-03-01"],
        "note": ["a", "b", "c"],
    })
    out = normalise_types(df)
    assert pd.api.types.is_numeric_dtype(out["amount"])
    assert out["amount"].iloc[0] == 1200.5
    assert pd.isna(out["amount"].iloc[2])
    assert pd.api.types.is_datetime64_any_dtype(out["when"])
    assert out["note"].dtype == object or pd.api.types.is_string_dtype(out["note"])
