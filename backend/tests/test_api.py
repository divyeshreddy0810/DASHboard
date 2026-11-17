from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import main
from app.planner import ClaudePlanner, HeuristicPlanner
from app.spec import PlannerResult
from app.store import Store


class FakeMessages:
    def __init__(self):
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        content = kwargs["messages"][0]["content"]
        _, _, request = content.partition("New request from the user:")
        dashboard = {
            "title": "Sales",
            "charts": [{"id": "rev", "type": "kpi", "title": "Revenue", "y": "revenue", "agg": "sum"}],
        }
        if "region" in request:
            dashboard["charts"].append(
                {"id": "by-region", "type": "bar", "title": "Revenue by region", "x": "region", "y": "revenue"}
            )
        parsed = PlannerResult.model_validate({"reply": "Done.", "dashboard": dashboard})
        return SimpleNamespace(stop_reason="end_turn", parsed_output=parsed)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "_store", Store(tmp_path))
    monkeypatch.setattr(main, "_planner", HeuristicPlanner())
    return TestClient(main.app)


def _upload(client, sample_bytes):
    res = client.post("/api/datasets", files={"file": ("sales.csv", sample_bytes, "text/csv")})
    assert res.status_code == 201, res.text
    return res.json()


def test_upload_and_heuristic_dashboard(client, sample_bytes):
    ds = _upload(client, sample_bytes)
    assert ds["profile"]["row_count"] == 1200

    res = client.post("/api/dashboards", data={"dataset_id": ds["id"]})
    assert res.status_code == 201, res.text
    body = res.json()
    types = [c["spec"]["type"] for c in body["charts"]]
    assert types[0] == "kpi"
    assert "line" in types and "bar" in types and "table" in types
    assert all(c["error"] is None for c in body["charts"]), [c["error"] for c in body["charts"]]

    again = client.get(f"/api/dashboards/{body['id']}").json()
    assert again["title"] == body["title"]
    assert client.get("/api/dashboards").json()[0]["id"] == body["id"]


def test_heuristic_chat_returns_502(client, sample_bytes):
    ds = _upload(client, sample_bytes)
    db = client.post("/api/dashboards", data={"dataset_id": ds["id"]}).json()
    res = client.post(f"/api/dashboards/{db['id']}/chat", json={"message": "add a pie"})
    assert res.status_code == 502


def test_rejects_unknown_file_type(client):
    res = client.post("/api/datasets", files={"file": ("notes.pdf", b"%PDF", "application/pdf")})
    assert res.status_code == 400


def test_claude_planner_edit_flow(client, sample_bytes, monkeypatch):
    fake = FakeMessages()
    planner = ClaudePlanner(client=SimpleNamespace(beta=SimpleNamespace(messages=fake)))
    monkeypatch.setattr(main, "_planner", planner)

    ds = _upload(client, sample_bytes)
    db = client.post("/api/dashboards", data={"dataset_id": ds["id"], "goal": "track revenue"}).json()
    assert [c["spec"]["id"] for c in db["charts"]] == ["rev"]

    res = client.post(f"/api/dashboards/{db['id']}/chat", json={"message": "break revenue down by region"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert [c["spec"]["id"] for c in body["charts"]] == ["rev", "by-region"]
    assert body["charts"][1]["data"]["rows"]
    assert [m["role"] for m in body["history"]] == ["user", "assistant", "user", "assistant"]

    call = fake.calls[-1]
    assert call["model"] == "claude-opus-5-5"
    assert call["output_format"] is PlannerResult
    assert "Current dashboard" in call["messages"][0]["content"]
