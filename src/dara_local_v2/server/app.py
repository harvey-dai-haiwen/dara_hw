"""FastAPI application entrypoint for dara_local_v2."""

from __future__ import annotations

import multiprocessing
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import build_api_router
from .queue import JobStore
from .worker import Worker


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = REPO_ROOT / "worker_db" / "jobs.sqlite"
DEFAULT_UPLOADS_DIR = Path.home() / ".dara-local-v2" / "uploads"
DEFAULT_FRONTEND_DIR = REPO_ROOT / "src" / "dara_local_v2" / "ui" / "dist"
DEFAULT_WORKDIR = Path.home() / "Documents" / "dara_analysis"
DEFAULT_INDEXES_DIR = REPO_ROOT / "indexes"


def _worker_main(job_db_path: Path, base_workdir: Path, indexes_dir: Path) -> None:
    store = JobStore(db_path=str(job_db_path))
    worker = Worker(
        store,
        base_workdir=base_workdir,
        indexes_dir=indexes_dir,
    )
    worker.run_forever()


def create_app(
    *,
    job_db_path: Optional[Path] = None,
    uploads_dir: Optional[Path] = None,
    frontend_dir: Optional[Path] = None,
    base_workdir: Optional[Path] = None,
    indexes_dir: Optional[Path] = None,
    start_worker: bool = True,
) -> FastAPI:
    job_db_path = job_db_path or DEFAULT_DB_PATH
    uploads_dir = uploads_dir or DEFAULT_UPLOADS_DIR
    frontend_dir = frontend_dir or DEFAULT_FRONTEND_DIR
    base_workdir = base_workdir or DEFAULT_WORKDIR
    indexes_dir = indexes_dir or DEFAULT_INDEXES_DIR

    uploads_dir.mkdir(parents=True, exist_ok=True)
    job_db_path.parent.mkdir(parents=True, exist_ok=True)

    job_store = JobStore(db_path=str(job_db_path))
    router = build_api_router(job_store, uploads_dir, base_workdir)

    worker_process: multiprocessing.Process | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal worker_process
        if start_worker:
            worker_process = multiprocessing.Process(
                target=_worker_main,
                args=(job_db_path, base_workdir, indexes_dir),
                daemon=True,
            )
            worker_process.start()
        try:
            yield
        finally:
            if worker_process and worker_process.is_alive():
                worker_process.terminate()
            job_store.close()

    app = FastAPI(lifespan=lifespan)
    app.state.job_store = job_store
    app.include_router(router, prefix="/api")

    if frontend_dir.exists():
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    return app


app = create_app()


def launch_app() -> None:
    """Launch uvicorn server for local development."""

    uvicorn.run(app, host="127.0.0.1", port=8899, reload=False)


__all__ = ["app", "create_app", "launch_app"]
