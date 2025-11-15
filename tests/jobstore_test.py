from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on sys.path for local testing
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dara_local_v2.server.queue import JobStore
from dara_local_v2.server.models import JobInput, JobStatus


def main() -> None:
    db_path = ROOT / "worker_db" / "test_jobs.sqlite"
    store = JobStore(db_path=str(db_path))

    job_input = JobInput(
        user="test-user",
        chemical_system="Y-Mo-O",
        required_elements=["Y", "Mo", "O"],
        exclude_elements=[],
        wavelength="Cu",
        instrument_profile="Aeris-fds-Pixcel1d-Medipix3",
        database="ICSD",
        mp_experimental_only=False,
        mp_max_e_above_hull=0.1,
        max_phases=100,
        pattern_filename="dummy.xy",
        pattern_path=str(ROOT / "dummy.xy"),
    )

    job_id = store.create_job(job_input)
    print("job_id:", job_id)

    summary = store.get_job(job_id)
    print("summary:", summary)

    pending = store.get_next_pending_job()
    print("next pending:", pending)

    store.update_status(job_id, JobStatus.RUNNING, started=True)
    updated = store.get_job(job_id)
    print("updated:", updated)

    loaded_input = store.get_job_input(job_id)
    print("loaded_input:", loaded_input)


if __name__ == "__main__":  # pragma: no cover
    main()
