"""Background worker for dara_local_v2 job execution."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import List

import numpy as np
from dara import search_phases
from plotly.utils import PlotlyJSONEncoder

from .models import Diagnostics, JobDetail, JobInput, JobStatus, PhaseTable, SolutionResult
from .phase_utils import export_phase_search_report, extract_phase_info
from .queue import JobStore

LOGGER = logging.getLogger("dara_local_v2.worker")

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from dara_adapter import prepare_phases_for_dara  # type: ignore  # noqa: E402


class Worker:
    """Worker that pulls jobs from JobStore and runs phase search."""

    def __init__(
        self,
        store: JobStore,
        *,
        repo_root: Path | None = None,
        base_workdir: Path | None = None,
        indexes_dir: Path | None = None,
        sleep_seconds: int = 2,
    ) -> None:
        self.store = store
        self.repo_root = repo_root or REPO_ROOT
        self.base_workdir = base_workdir or (Path.home() / "Documents" / "dara_analysis")
        self.indexes_dir = indexes_dir or (self.repo_root / "indexes")
        self.sleep_seconds = sleep_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run_forever(self) -> None:
        LOGGER.info("Worker loop started")
        while True:
            job = self.store.get_next_pending_job()
            if job is None:
                time.sleep(self.sleep_seconds)
                continue
            try:
                self.process_job(job.job_id)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Job %s failed: %s", job.job_id, exc)

    def process_job(self, job_id: str) -> None:
        LOGGER.info("Processing job %s", job_id)
        job_input = self.store.get_job_input(job_id)
        if job_input is None:
            self._mark_failed(job_id, "Missing job input")
            return

        self.store.update_status(job_id, JobStatus.RUNNING, started=True)
        try:
            detail = self._execute_job(job_id, job_input)
            LOGGER.info("Job %s completed with %d solutions", job_id, len(detail.solutions))
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Job %s raised exception", job_id)
            self._mark_failed(job_id, str(exc))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _execute_job(self, job_id: str, job_input: JobInput) -> JobDetail:
        pattern_path = Path(job_input.pattern_path)
        if not pattern_path.exists():
            raise FileNotFoundError(f"Pattern file not found: {pattern_path}")

        work_dirs = self._ensure_workdirs(job_input)
        diagnostics = self._compute_diagnostics(pattern_path)

        all_cifs = self._collect_cifs(job_input, work_dirs["custom_cif_dir"])
        if not all_cifs:
            raise RuntimeError(
                "No CIF phases found. Please check indexes/required elements configuration."
            )

        LOGGER.info("Job %s: running phase search on %d phases", job_id, len(all_cifs))
        search_results = search_phases(
            pattern_path=str(pattern_path),
            phases=all_cifs,
            wavelength=job_input.wavelength,
            instrument_profile=job_input.instrument_profile,
        )

        solutions: List[SolutionResult] = []
        for idx, solution in enumerate(search_results, start=1):
            fig = solution.visualize()
            phase_df = extract_phase_info(
                solution,
                custom_cif_dir=work_dirs["custom_cif_dir"],
                database=job_input.database,
            )
            phases_table = PhaseTable(
                columns=list(phase_df.columns),
                rows=phase_df.to_dict(orient="records"),
            )

            report_dir = export_phase_search_report(
                solution,
                idx,
                work_dirs["reports_dir"],
                custom_cif_dir=work_dirs["custom_cif_dir"],
                database=job_input.database,
            )
            zip_path = self._make_zip(report_dir)

            solutions.append(
                SolutionResult(
                    index=idx,
                    rwp=float(solution.refinement_result.lst_data.rwp),
                    num_phases=len(solution.phases),
                    plotly_figure=self._figure_to_json(fig),
                    phases_table=phases_table,
                    report_zip_url=str(zip_path),
                )
            )

        self.store.update_status(
            job_id,
            JobStatus.COMPLETED,
            num_phases=len(all_cifs),
            finished=True,
        )
        summary = self.store.get_job(job_id)
        detail = JobDetail(job=summary, diagnostics=diagnostics, solutions=solutions)
        self.store.save_job_detail(job_id, detail)
        return detail

    def _collect_cifs(self, job_input: JobInput, custom_cif_dir: Path) -> List[str]:
        database = job_input.database.upper()
        cifs: List[str] = []

        if database != "NONE":
            index_path = self._get_index_path(database)
            if not index_path.exists():
                raise FileNotFoundError(f"Index not found for {database}: {index_path}")

            prepare_kwargs = {
                "index_path": index_path,
                "required_elements": job_input.required_elements,
                "exclude_elements": job_input.exclude_elements,
                "max_phases": job_input.max_phases,
            }
            if database == "MP":
                prepare_kwargs.update(
                    {
                        "experimental_only": job_input.mp_experimental_only,
                        "include_theoretical": not job_input.mp_experimental_only,
                        "max_e_above_hull": job_input.mp_max_e_above_hull,
                    }
                )

            cifs.extend(prepare_phases_for_dara(**prepare_kwargs))

        if custom_cif_dir.exists():
            for cif_path in custom_cif_dir.glob("*.cif"):
                cifs.append(str(cif_path.resolve()))

        return cifs

    def _get_index_path(self, database: str) -> Path:
        mapping = {
            "COD": self.indexes_dir / "cod_index_filled.parquet",
            "ICSD": self.indexes_dir / "icsd_index_filled.parquet",
            "MP": self.indexes_dir / "mp_index.parquet",
        }
        if database not in mapping:
            raise ValueError(f"Unsupported database: {database}")
        return mapping[database]

    def _ensure_workdirs(self, job_input: JobInput) -> dict:
        chem_dir_name = job_input.chemical_system.replace("-", "")
        base_dir = self.base_workdir / chem_dir_name
        custom_dir = base_dir / "custom_cifs"
        reports_dir = base_dir / "reports"
        base_dir.mkdir(parents=True, exist_ok=True)
        custom_dir.mkdir(exist_ok=True)
        reports_dir.mkdir(exist_ok=True)
        return {
            "base_dir": base_dir,
            "custom_cif_dir": custom_dir,
            "reports_dir": reports_dir,
        }

    def _compute_diagnostics(self, pattern_path: Path) -> Diagnostics:
        try:
            data = np.loadtxt(pattern_path)
            if data.ndim != 2 or data.shape[1] < 2:
                raise ValueError("Pattern file must have two columns")
            two_theta = data[:, 0]
            intensity = data[:, 1]
            checks = {
                "intensity": "ok" if intensity.max() >= 100 else "warn",
                "num_points": "ok" if len(two_theta) >= 100 else "warn",
                "two_theta_range": "ok"
                if (two_theta.max() - two_theta.min()) >= 20
                else "warn",
            }
            return Diagnostics(
                two_theta_min=float(two_theta.min()),
                two_theta_max=float(two_theta.max()),
                intensity_min=float(intensity.min()),
                intensity_max=float(intensity.max()),
                num_points=int(two_theta.size),
                checks=checks,
            )
        except Exception:  # noqa: BLE001
            return Diagnostics(
                two_theta_min=0.0,
                two_theta_max=0.0,
                intensity_min=0.0,
                intensity_max=0.0,
                num_points=0,
                checks={"intensity": "warn", "num_points": "warn", "two_theta_range": "warn"},
            )

    def _make_zip(self, report_dir: Path) -> Path:
        import shutil

        archive_path = shutil.make_archive(str(report_dir), "zip", root_dir=report_dir)
        return Path(archive_path)

    def _figure_to_json(self, fig):
        import json

        json_str = json.dumps(fig, cls=PlotlyJSONEncoder)
        return json.loads(json_str)

    def _mark_failed(self, job_id: str, message: str) -> None:
        self.store.update_status(
            job_id,
            JobStatus.FAILED,
            error_message=message,
            finished=True,
        )
        summary = self.store.get_job(job_id)
        detail = JobDetail(
            job=summary,
            diagnostics=Diagnostics(
                two_theta_min=0.0,
                two_theta_max=0.0,
                intensity_min=0.0,
                intensity_max=0.0,
                num_points=0,
                checks={"intensity": "warn", "num_points": "warn", "two_theta_range": "warn"},
            ),
            solutions=[],
        )
        self.store.save_job_detail(job_id, detail)
