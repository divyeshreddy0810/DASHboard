"""File-backed storage for datasets and dashboards."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .profiling import read_table
from .spec import DashboardSpec


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root or os.environ.get("DASHBOARD_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
        (self.root / "datasets").mkdir(parents=True, exist_ok=True)
        (self.root / "dashboards").mkdir(parents=True, exist_ok=True)
        self._frames: Dict[str, pd.DataFrame] = {}

    # datasets -----------------------------------------------------------
    def save_dataset(self, filename: str, content: bytes, df: pd.DataFrame, profile: Dict[str, Any]) -> Dict[str, Any]:
        ds_id = uuid.uuid4().hex[:12]
        folder = self.root / "datasets" / ds_id
        folder.mkdir(parents=True)
        safe_name = Path(filename).name
        (folder / safe_name).write_bytes(content)
        meta = {"id": ds_id, "name": Path(safe_name).stem, "filename": safe_name,
                "created_at": _now(), "profile": profile}
        (folder / "meta.json").write_text(json.dumps(meta, default=str))
        self._frames[ds_id] = df
        return meta

    def get_dataset(self, ds_id: str) -> Optional[Dict[str, Any]]:
        path = self.root / "datasets" / Path(ds_id).name / "meta.json"
        return json.loads(path.read_text()) if path.exists() else None

    def list_datasets(self) -> List[Dict[str, Any]]:
        out = []
        for p in sorted((self.root / "datasets").glob("*/meta.json")):
            meta = json.loads(p.read_text())
            out.append({k: meta[k] for k in ("id", "name", "filename", "created_at")} |
                       {"rows": meta["profile"]["row_count"]})
        return sorted(out, key=lambda m: m["created_at"], reverse=True)

    def frame(self, ds_id: str) -> pd.DataFrame:
        if ds_id not in self._frames:
            meta = self.get_dataset(ds_id)
            if meta is None:
                raise KeyError(ds_id)
            content = (self.root / "datasets" / ds_id / meta["filename"]).read_bytes()
            self._frames[ds_id] = read_table(meta["filename"], content)
        return self._frames[ds_id]

    # dashboards ---------------------------------------------------------
    def save_dashboard(self, record: Dict[str, Any]) -> Dict[str, Any]:
        record.setdefault("id", uuid.uuid4().hex[:12])
        record.setdefault("created_at", _now())
        record["updated_at"] = _now()
        path = self.root / "dashboards" / f"{record['id']}.json"
        path.write_text(json.dumps(record, default=str))
        return record

    def get_dashboard(self, db_id: str) -> Optional[Dict[str, Any]]:
        path = self.root / "dashboards" / f"{Path(db_id).name}.json"
        return json.loads(path.read_text()) if path.exists() else None

    def list_dashboards(self) -> List[Dict[str, Any]]:
        out = []
        for p in (self.root / "dashboards").glob("*.json"):
            r = json.loads(p.read_text())
            out.append({"id": r["id"], "title": r["spec"]["title"], "dataset_id": r["dataset_id"],
                        "updated_at": r["updated_at"]})
        return sorted(out, key=lambda r: r["updated_at"], reverse=True)

    @staticmethod
    def spec_of(record: Dict[str, Any]) -> DashboardSpec:
        return DashboardSpec.model_validate(record["spec"])
