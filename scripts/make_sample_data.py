"""Generate sample_data/sales.csv for local testing."""

from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
n = 1200
regions = ["North", "South", "East", "West"]
categories = {"Electronics": 420.0, "Furniture": 260.0, "Office Supplies": 35.0, "Software": 180.0}
channels = ["Online", "Retail", "Partner"]

dates = pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 640, n), unit="D")
cat = rng.choice(list(categories), n, p=[0.3, 0.2, 0.35, 0.15])
qty = rng.integers(1, 12, n)
unit_price = np.array([categories[c] for c in cat]) * rng.uniform(0.7, 1.3, n)
revenue = (qty * unit_price).round(2)
cost = (revenue * rng.uniform(0.45, 0.8, n)).round(2)

df = pd.DataFrame({
    "order_id": [f"SO-{100000 + i}" for i in range(n)],
    "order_date": dates.strftime("%Y-%m-%d"),
    "region": rng.choice(regions, n, p=[0.3, 0.2, 0.28, 0.22]),
    "channel": rng.choice(channels, n, p=[0.5, 0.35, 0.15]),
    "category": cat,
    "quantity": qty,
    "unit_price": unit_price.round(2),
    "revenue": revenue,
    "cost": cost,
    "profit": (revenue - cost).round(2),
    "customer_rating": rng.choice([1, 2, 3, 4, 5], n, p=[0.04, 0.06, 0.2, 0.4, 0.3]),
}).sort_values("order_date")

out = Path(__file__).resolve().parent.parent / "sample_data" / "sales.csv"
df.to_csv(out, index=False)
print(f"wrote {len(df)} rows to {out}")
