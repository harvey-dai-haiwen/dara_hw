from __future__ import annotations

import sys
from pathlib import Path
from time import sleep

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dara_local_v2.server.app import create_app
from dara_local_v2.server.queue import JobStore
from dara_local_v2.server.worker import Worker

PATTERN_PATH = Path(r"D:\XRD_Analysis\DTMA_YMoO3\20231212_YCl3Onepot_1200.xy")


def main() -> None:
    if not PATTERN_PATH.exists():
        raise FileNotFoundError(f"Pattern file missing: {PATTERN_PATH}")

    db_path = ROOT / "worker_db" / "api_e2e.sqlite"
    uploads_dir = ROOT / "tmp_uploads"

    app = create_app(
        job_db_path=db_path,
        uploads_dir=uploads_dir,
        start_worker=False,
    )

    client = TestClient(app)

    files = {"pattern_file": (PATTERN_PATH.name, PATTERN_PATH.open("rb"), "text/plain")}
    data = {
        "user": "api-test",
        "chemical_system": "Y-Mo-O",
        "required_elements": "[\"Y\", \"Mo\", \"O\"]",
        "exclude_elements": "[]",
        "wavelength": "Cu",
        "instrument_profile": "Aeris-fds-Pixcel1d-Medipix3",
        "database": "ICSD",
        "mp_experimental_only": "false",
        "mp_max_e_above_hull": "0.1",
        "max_phases": "200",
    }

    response = client.post("/api/jobs", data=data, files=files)
    response.raise_for_status()
    payload = response.json()
    job_id = payload["job_id"]
    print("Created job", job_id)

    store = JobStore(db_path=str(db_path))
    worker = Worker(store)
    worker.process_job(job_id)

    detail_response = client.get(f"/api/jobs/{job_id}")
    detail_response.raise_for_status()
    detail = detail_response.json()
    print("Solutions", len(detail["solutions"]))
    assert len(detail["solutions"]) >= 1

    zip_resp = client.get(f"/api/jobs/{job_id}/download/1/zip")
    zip_resp.raise_for_status()
    print("ZIP bytes", len(zip_resp.content))


if __name__ == "__main__":
    main()
