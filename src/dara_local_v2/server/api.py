"""FastAPI router for dara_local_v2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from .models import JobDetail, JobInput, JobStatus
from .queue import JobStore


def build_api_router(store: JobStore, uploads_dir: Path) -> APIRouter:
    """Construct API router bound to the provided JobStore."""

    router = APIRouter()
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    @router.post("/jobs")
    async def create_job(
        pattern_file: UploadFile = File(...),
        user: str = Form(...),
        chemical_system: str = Form(...),
        required_elements: str = Form("[]"),
        exclude_elements: str = Form("[]"),
        wavelength: str = Form("Cu"),
        instrument_profile: str = Form("Aeris-fds-Pixcel1d-Medipix3"),
        database: str = Form("ICSD"),
        mp_experimental_only: bool = Form(False),
        mp_max_e_above_hull: float = Form(0.1),
        max_phases: int = Form(500),
    ) -> dict:
        try:
            required = json.loads(required_elements)
            excluded = json.loads(exclude_elements)
        except json.JSONDecodeError as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Invalid element list: {exc}") from exc

        if not isinstance(required, list) or not isinstance(excluded, list):
            raise HTTPException(status_code=400, detail="Element fields must be JSON arrays")

        dest_path = uploads_dir / pattern_file.filename
        with dest_path.open("wb") as fp:
            fp.write(await pattern_file.read())

        job_input = JobInput(
            user=user,
            chemical_system=chemical_system,
            required_elements=required,
            exclude_elements=excluded,
            wavelength=wavelength,
            instrument_profile=instrument_profile,
            database=database,
            mp_experimental_only=mp_experimental_only,
            mp_max_e_above_hull=mp_max_e_above_hull,
            max_phases=max_phases,
            pattern_filename=pattern_file.filename,
            pattern_path=str(dest_path),
        )

        job_id = store.create_job(job_input)
        return {"job_id": job_id, "status": JobStatus.PENDING}

    # ------------------------------------------------------------------
    @router.get("/jobs")
    def list_jobs(
        status: Optional[JobStatus] = Query(default=None),
        user: Optional[str] = Query(default=None),
        limit: Optional[int] = Query(default=None, ge=1),
        offset: Optional[int] = Query(default=None, ge=0),
    ) -> dict:
        jobs = store.list_jobs(status=status, user=user, limit=limit, offset=offset)
        return {"jobs": [job.model_dump() for job in jobs], "total": len(jobs)}

    # ------------------------------------------------------------------
    @router.get("/jobs/{job_id}")
    def get_job_detail(job_id: str) -> JobDetail:
        detail = store.load_job_detail(job_id)
        if detail is None:
            summary = store.get_job(job_id)
            if summary is None:
                raise HTTPException(status_code=404, detail="Job not found")
            return JobDetail(
                job=summary,
                diagnostics=None,  # type: ignore[arg-type]
                solutions=[],
            )
        return detail

    # ------------------------------------------------------------------
    @router.get("/jobs/{job_id}/download/{solution_index}/zip")
    def download_report(job_id: str, solution_index: int) -> FileResponse:
        detail = store.load_job_detail(job_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Job detail not found")

        match = next((s for s in detail.solutions if s.index == solution_index), None)
        if match is None:
            raise HTTPException(status_code=404, detail="Solution not found")

        path = Path(match.report_zip_url)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Report file missing")

        return FileResponse(path, filename=path.name)

    return router
