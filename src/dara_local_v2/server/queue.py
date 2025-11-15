"""SQLite-backed job store for dara_local_v2."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Sequence

from .models import JobDetail, JobInput, JobStatus, JobSummary

ISO_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"


def _now() -> str:
    return datetime.now(tz=timezone.utc).strftime(ISO_FMT)


class JobStore:
    """Persist job metadata and results using SQLite."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    user TEXT NOT NULL,
                    pattern_filename TEXT NOT NULL,
                    database TEXT NOT NULL,
                    status TEXT NOT NULL,
                    num_phases INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    error_message TEXT,
                    job_input_json TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS job_details (
                    job_id TEXT PRIMARY KEY,
                    detail_json TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
                )
                """
            )

    def close(self) -> None:
        self._conn.close()

    def create_job(self, job_input: JobInput) -> str:
        job_id = uuid.uuid4().hex
        created_at = _now()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO jobs (
                    job_id, user, pattern_filename, database, status,
                    created_at, job_input_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    job_input.user,
                    job_input.pattern_filename,
                    job_input.database,
                    JobStatus.PENDING.value,
                    created_at,
                    json.dumps(job_input.model_dump()),
                ),
            )
        return job_id

    def get_job(self, job_id: str) -> Optional[JobSummary]:
        row = self._conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        return self._row_to_summary(row) if row else None

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        user: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[JobSummary]:
        clauses: List[str] = []
        params: List[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status.value)
        if user:
            clauses.append("user LIKE ?")
            params.append(f"%{user}%")
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        paging = ""
        if limit is not None:
            paging += " LIMIT ?"
            params.append(limit)
        if offset is not None:
            paging += " OFFSET ?"
            params.append(offset)
        rows = self._conn.execute(
            f"SELECT * FROM jobs {where_sql} ORDER BY datetime(created_at) ASC{paging}",
            tuple(params),
        ).fetchall()
        return [self._row_to_summary(row) for row in rows]

    def get_next_pending_job(self) -> Optional[JobSummary]:
        row = self._conn.execute(
            """
            SELECT * FROM jobs
            WHERE status = ?
            ORDER BY datetime(created_at) ASC
            LIMIT 1
            """,
            (JobStatus.PENDING.value,),
        ).fetchone()
        return self._row_to_summary(row) if row else None

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        *,
        error_message: Optional[str] = None,
        num_phases: Optional[int] = None,
        started: bool = False,
        finished: bool = False,
    ) -> None:
        fields: List[str] = ["status = ?"]
        params: List[Any] = [status.value]
        if error_message is not None:
            fields.append("error_message = ?")
            params.append(error_message)
        if num_phases is not None:
            fields.append("num_phases = ?")
            params.append(num_phases)
        if started:
            fields.append("started_at = ?")
            params.append(_now())
        if finished:
            fields.append("finished_at = ?")
            params.append(_now())
        params.append(job_id)
        with self._conn:
            self._conn.execute(
                f"UPDATE jobs SET {', '.join(fields)} WHERE job_id = ?",
                tuple(params),
            )

    def get_job_input(self, job_id: str) -> Optional[JobInput]:
        row = self._conn.execute(
            "SELECT job_input_json FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        data = json.loads(row[0])
        return JobInput.model_validate(data)

    def save_job_detail(self, job_id: str, detail: JobDetail) -> None:
        detail_json = json.dumps(detail.model_dump())
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO job_details (job_id, detail_json)
                VALUES (?, ?) ON CONFLICT(job_id)
                DO UPDATE SET detail_json = excluded.detail_json
                """,
                (job_id, detail_json),
            )

    def load_job_detail(self, job_id: str) -> Optional[JobDetail]:
        row = self._conn.execute(
            "SELECT detail_json FROM job_details WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        return JobDetail.model_validate(json.loads(row[0]))

    def _row_to_summary(self, row: sqlite3.Row) -> JobSummary:
        return JobSummary(
            job_id=row["job_id"],
            user=row["user"],
            pattern_filename=row["pattern_filename"],
            database=row["database"],
            status=JobStatus(row["status"]),
            num_phases=row["num_phases"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            error_message=row["error_message"],
        )

    def __del__(self) -> None:  # pragma: no cover - best effort cleanup
        try:
            self.close()
        except Exception:  # noqa: BLE001
            pass
