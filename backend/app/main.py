from __future__ import annotations

import os
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .engine import render_dashboard
from .planner import PlannerUnavailable, default_planner
from .profiling import UnsupportedFile, profile_frame, read_table
from .spec import DashboardSpec
from .store import Store

MAX_UPLOAD_BYTES = int(os.environ.get("DASHBOARD_MAX_UPLOAD_MB", "50")) * 1024 * 1024

app = FastAPI(title="Dashboard API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("DASHBOARD_CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

_store: Optional[Store] = None
_planner = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store


def get_planner():
    global _planner
    if _planner is None:
        _planner = default_planner()
    return _planner


class ChatRequest(BaseModel):
    message: str


def _view(store: Store, record: dict) -> dict:
    spec = Store.spec_of(record)
    df = store.frame(record["dataset_id"])
    return {
        "id": record["id"],
        "dataset_id": record["dataset_id"],
        "title": spec.title,
        "description": spec.description,
        "charts": render_dashboard(df, spec.charts),
        "history": record.get("history", []),
        "planner": record.get("planner"),
        "updated_at": record["updated_at"],
    }


@app.get("/api/health")
def health(planner=Depends(get_planner)):
    return {"ok": True, "planner": planner.name}


@app.get("/api/datasets")
def list_datasets(store: Store = Depends(get_store)):
    return store.list_datasets()


@app.post("/api/datasets", status_code=201)
async def upload_dataset(file: UploadFile = File(...), store: Store = Depends(get_store)):
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File is too large.")
    try:
        df = read_table(file.filename or "upload.csv", content)
    except UnsupportedFile as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Could not read the file: {exc}") from exc
    return store.save_dataset(file.filename or "upload.csv", content, df, profile_frame(df))


@app.get("/api/datasets/{ds_id}")
def get_dataset(ds_id: str, store: Store = Depends(get_store)):
    meta = store.get_dataset(ds_id)
    if meta is None:
        raise HTTPException(404, "Dataset not found.")
    return meta


@app.get("/api/dashboards")
def list_dashboards(store: Store = Depends(get_store)):
    return store.list_dashboards()


@app.post("/api/dashboards", status_code=201)
def create_dashboard(
    dataset_id: str = Form(...),
    goal: Optional[str] = Form(None),
    store: Store = Depends(get_store),
    planner=Depends(get_planner),
):
    meta = store.get_dataset(dataset_id)
    if meta is None:
        raise HTTPException(404, "Dataset not found.")
    try:
        result = planner.create(meta["profile"], meta["name"], goal)
    except PlannerUnavailable as exc:
        raise HTTPException(502, str(exc)) from exc
    history = []
    if goal:
        history.append({"role": "user", "content": goal})
    history.append({"role": "assistant", "content": result.reply})
    record = store.save_dashboard({
        "dataset_id": dataset_id,
        "spec": result.dashboard.model_dump(),
        "history": history,
        "planner": planner.name,
    })
    return _view(store, record)


@app.get("/api/dashboards/{db_id}")
def get_dashboard(db_id: str, store: Store = Depends(get_store)):
    record = store.get_dashboard(db_id)
    if record is None:
        raise HTTPException(404, "Dashboard not found.")
    return _view(store, record)


@app.put("/api/dashboards/{db_id}/spec")
def replace_spec(db_id: str, spec: DashboardSpec, store: Store = Depends(get_store)):
    record = store.get_dashboard(db_id)
    if record is None:
        raise HTTPException(404, "Dashboard not found.")
    record["spec"] = spec.model_dump()
    return _view(store, store.save_dashboard(record))


@app.post("/api/dashboards/{db_id}/chat")
def chat(db_id: str, body: ChatRequest, store: Store = Depends(get_store), planner=Depends(get_planner)):
    record = store.get_dashboard(db_id)
    if record is None:
        raise HTTPException(404, "Dashboard not found.")
    message = body.message.strip()
    if not message:
        raise HTTPException(400, "Message is empty.")
    meta = store.get_dataset(record["dataset_id"])
    try:
        result = planner.edit(meta["profile"], meta["name"], Store.spec_of(record),
                              record.get("history", []), message)
    except PlannerUnavailable as exc:
        raise HTTPException(502, str(exc)) from exc
    record["spec"] = result.dashboard.model_dump()
    record.setdefault("history", []).extend([
        {"role": "user", "content": message},
        {"role": "assistant", "content": result.reply},
    ])
    return _view(store, store.save_dashboard(record))
