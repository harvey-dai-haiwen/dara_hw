"""Focused API router tests for database selection."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

import dara.server.api_router as api_router


class DummyJob:
    uuid = "job-123"

    @staticmethod
    def as_dict():
        return {"uuid": "job-123"}


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(api_router.router)
    return app


def test_submit_uses_selected_database(monkeypatch):
    captured = {}

    monkeypatch.setattr(api_router, "load_pattern", lambda _: object())
    monkeypatch.setattr(api_router, "add_job_to_queue", lambda job, user: 7)

    def fake_make(self, pattern, **kwargs):
        captured["database_names"] = [type(db).__name__ for db in kwargs["cif_dbs"]]
        return DummyJob()

    monkeypatch.setattr(api_router.PhaseSearchMaker, "make", fake_make)

    client = TestClient(_build_app())
    response = client.post(
        "/api/submit",
        data={
            "precursor_formulas": '["Fe2O3"]',
            "user": "tester",
            "temperature": "-274",
            "use_rxn_predictor": "false",
            "database": "ICSD",
        },
        files={"pattern_file": ("pattern.xy", b"1 1\n2 2\n", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "submitted", "wf_id": 7}
    assert captured["database_names"] == ["ICSDDatabase"]


def test_submit_supports_all_database_selection(monkeypatch):
    captured = {}

    monkeypatch.setattr(api_router, "load_pattern", lambda _: object())
    monkeypatch.setattr(api_router, "add_job_to_queue", lambda job, user: 8)

    def fake_make(self, pattern, **kwargs):
        captured["database_names"] = [type(db).__name__ for db in kwargs["cif_dbs"]]
        return DummyJob()

    monkeypatch.setattr(api_router.PhaseSearchMaker, "make", fake_make)

    client = TestClient(_build_app())
    response = client.post(
        "/api/submit",
        data={
            "precursor_formulas": '["Fe2O3"]',
            "user": "tester",
            "temperature": "-274",
            "use_rxn_predictor": "false",
            "database": "ALL",
        },
        files={"pattern_file": ("pattern.xy", b"1 1\n2 2\n", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "submitted", "wf_id": 8}
    assert captured["database_names"] == ["CODDatabase", "ICSDDatabase", "MPDatabase"]


def test_submit_rejects_unknown_database(monkeypatch):
    monkeypatch.setattr(api_router, "load_pattern", lambda _: object())

    client = TestClient(_build_app())
    response = client.post(
        "/api/submit",
        data={
            "precursor_formulas": '["Fe2O3"]',
            "user": "tester",
            "temperature": "-274",
            "use_rxn_predictor": "false",
            "database": "not-a-db",
        },
        files={"pattern_file": ("pattern.xy", b"1 1\n2 2\n", "text/plain")},
    )

    assert response.status_code == 400
    assert "Unsupported database" in response.json()["detail"]