from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dara_local_v2.server.models import JobInput
from dara_local_v2.server.queue import JobStore
from dara_local_v2.server.worker import Worker


def main() -> None:
    pattern_path = Path(r"D:\XRD_Analysis\DTMA_YMoO3\20231212_YCl3Onepot_1200.xy")
    if not pattern_path.exists():
        raise FileNotFoundError(f"Missing test pattern: {pattern_path}")

    db_path = ROOT / "worker_db" / "worker_test.sqlite"
    store = JobStore(db_path=str(db_path))

    job_input = JobInput(
        user="test-worker",
        chemical_system="Y-Mo-O",
        required_elements=["Y", "Mo", "O"],
        exclude_elements=[],
        wavelength="Cu",
        instrument_profile="Aeris-fds-Pixcel1d-Medipix3",
        database="ICSD",
        mp_experimental_only=False,
        mp_max_e_above_hull=0.1,
        max_phases=200,
        pattern_filename=pattern_path.name,
        pattern_path=str(pattern_path),
    )

    job_id = store.create_job(job_input)
    print("Created job", job_id)

    worker = Worker(store)
    worker.process_job(job_id)

    detail = store.load_job_detail(job_id)
    print("Job detail solutions:", len(detail.solutions) if detail else None)


if __name__ == "__main__":  # pragma: no cover
    main()
