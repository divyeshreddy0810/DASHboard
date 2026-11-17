# DASHboard

Upload a dataset, get a dashboard. The backend profiles each column, picks chart
types, computes the aggregates each chart needs, and lets you change the dashboard
by describing what you want.

Current scope is file uploads (CSV, TSV, Excel, JSON). Database connectors come next.

## How it works

1. **Profile** – `backend/app/profiling.py` reads the file, fixes column types
   (numbers stored as text, dates, currency) and builds a summary per column:
   kind, null rate, cardinality, range, top values.
2. **Plan** – `backend/app/planner.py` turns the profile into a dashboard spec
   (`backend/app/spec.py`). With `ANTHROPIC_API_KEY` set it asks Claude, which
   only sees the profile, not the rows. Without a key a rule-based planner builds
   a reasonable first dashboard.
3. **Compute** – `backend/app/engine.py` runs each chart spec against the data
   (filters, grouping, time buckets, aggregation) and returns only what the chart
   draws.
4. **Edit** – chat messages go back to the planner with the current spec, and the
   updated spec is recomputed.

Dashboards are stored as specs, so they can be recomputed when the data changes.

## Running locally

Requirements: Python 3.11+, Node 20+.

```bash
# backend
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
export ANTHROPIC_API_KEY=...   # optional, enables Claude planning and chat edits
cd backend && ../.venv/bin/uvicorn app.main:app --reload --port 8000
```

```bash
# frontend
cd frontend
npm install
npm run dev   # http://localhost:5173, proxies /api to :8000
```

`sample_data/sales.csv` is a generated dataset for trying it out
(`python scripts/make_sample_data.py` regenerates it).

### Configuration

| Variable | Default | |
|---|---|---|
| `ANTHROPIC_API_KEY` | unset | Enables the Claude planner |
| `DASHBOARD_MODEL` | `claude-opus-5-5` | Model used by the planner |
| `DASHBOARD_DATA_DIR` | `backend/data` | Where uploads and dashboards are stored |
| `DASHBOARD_MAX_UPLOAD_MB` | `50` | Upload size limit |
| `DASHBOARD_CORS_ORIGINS` | `http://localhost:5173` | Comma-separated |

## API

| Method | Path | |
|---|---|---|
| `POST` | `/api/datasets` | Upload a file (multipart `file`) |
| `GET` | `/api/datasets/{id}` | Dataset metadata and profile |
| `POST` | `/api/dashboards` | Create from `dataset_id`, optional `goal` |
| `GET` | `/api/dashboards/{id}` | Spec plus computed chart data |
| `POST` | `/api/dashboards/{id}/chat` | `{"message": "..."}` – edit the dashboard |
| `PUT` | `/api/dashboards/{id}/spec` | Replace the spec directly |

## Tests

```bash
cd backend && ../.venv/bin/python -m pytest
```

## Roadmap

- [x] File upload, profiling, chart selection, chat edits
- [ ] Connectors: Postgres, MySQL, BigQuery, MongoDB, Redshift/Athena
- [ ] Saved dashboards that refresh on a schedule
- [ ] Auth, encrypted credential storage, multi-user, deployment
