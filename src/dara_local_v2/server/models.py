"""Pydantic models for dara_local_v2 job handling."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Enumeration of possible job statuses."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobInput(BaseModel):
    """User-submitted configuration for a job."""

    user: str
    chemical_system: str
    required_elements: List[str]
    exclude_elements: List[str]
    wavelength: str
    instrument_profile: str
    database: str
    mp_experimental_only: bool = False
    mp_max_e_above_hull: float = 0.1
    max_phases: int = 500
    pattern_filename: str
    pattern_path: str


class JobSummary(BaseModel):
    """Summary information for displaying job status."""

    job_id: str
    user: str
    pattern_filename: str
    database: str
    status: JobStatus
    num_phases: int = 0
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error_message: Optional[str] = None


class Diagnostics(BaseModel):
    """Diagnostic info computed from the XRD pattern."""

    two_theta_min: float
    two_theta_max: float
    intensity_min: float
    intensity_max: float
    num_points: int
    checks: Dict[str, str]


class PhaseTable(BaseModel):
    """Tabular representation of extracted phase information."""

    columns: List[str]
    rows: List[Dict[str, Any]]


class SolutionResult(BaseModel):
    """Result metadata for a single solution."""

    index: int
    rwp: float
    num_phases: int
    plotly_figure: Dict[str, Any]
    phases_table: PhaseTable
    report_zip_url: str


class JobDetail(BaseModel):
    """Full job detail including diagnostics and all solutions."""

    job: JobSummary
    diagnostics: Optional[Diagnostics] = None
    solutions: List[SolutionResult] = Field(default_factory=list)
