"""Perform refinements with Dara refinement backends."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from dara.result import RefinementResult


class RefinementPhase(BaseModel, frozen=True):
    """
    Input phase for refinement.

    Contains the path to the phase file and the specific parameters for the phase.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    path: Path = Field(..., description="The path to the phase file.")
    params: dict[str, Any] = Field(
        default_factory=dict,
        kw_only=True,
        description="The specific parameters for the phase.",
    )

    @field_validator("path", mode="before")
    @classmethod
    def _validate_path(cls, v):
        return Path(v)

    def __hash__(self):
        return hash(self.path)

    def __eq__(self, other: RefinementPhase):
        return self.path == other.path

    @classmethod
    def make(cls, path_obj: RefinementPhase | Path | str) -> RefinementPhase:
        """
        Make an RefinementPhase object from a path object. If the path object is already an
        RefinementPhase object, return it.
        If the path object is a string or Path object, create an RefinementPhase object
        with the path object with no specific parameters (the default parameters will be used).

        Args:
            path_obj: the path object, can be a string, Path object, or RefinementPhase object.

        Returns
        -------
            RefinementPhase object
        """
        return (
            path_obj
            if isinstance(path_obj, RefinementPhase)
            else RefinementPhase(path=Path(path_obj))
        )


def do_refinement(
    pattern_path: Path | str,
    phases: list[RefinementPhase | Path | str],
    wavelength: Literal["Cu", "Co", "Cr", "Fe", "Mo"] | float = "Cu",
    instrument_profile: str | Path = "Aeris-fds-Pixcel1d-Medipix3",
    working_dir: Path | str | None = None,
    phase_params: dict | None = None,
    refinement_params: dict | None = None,
    backend: Literal["bgmn", "gsas", "fullprof"] | str = "bgmn",
    backend_options: dict[str, Any] | None = None,
    show_progress: bool = False,
) -> RefinementResult:
    """Refine structures with the selected backend.

    The default backend is BGMN and preserves the historical Dara behavior.
    GSAS-II and FullProf are opt-in confirmation backends.
    """
    from dara.refinement_backends import run_refinement_backend

    return run_refinement_backend(
        pattern_path=pattern_path,
        phases=phases,
        wavelength=wavelength,
        instrument_profile=instrument_profile,
        working_dir=working_dir,
        phase_params=phase_params,
        refinement_params=refinement_params,
        backend=backend,
        backend_options=backend_options,
        show_progress=show_progress,
    )


def do_refinement_no_saving(
    pattern_path: Path,
    phases: list[RefinementPhase | Path | str],
    wavelength: Literal["Cu", "Co", "Cr", "Fe", "Mo"] | float = "Cu",
    instrument_profile: str | Path = "Aeris-fds-Pixcel1d-Medipix3",
    phase_params: dict | None = None,
    refinement_params: dict | None = None,
    backend: Literal["bgmn", "gsas", "fullprof"] | str = "bgmn",
    backend_options: dict[str, Any] | None = None,
    show_progress: bool = False,
) -> RefinementResult:
    """Refine the structure in a temporary directory without saving."""
    with tempfile.TemporaryDirectory() as tmpdir:
        working_dir = Path(tmpdir)

        return do_refinement(
            pattern_path=pattern_path,
            phases=phases,
            wavelength=wavelength,
            instrument_profile=instrument_profile,
            working_dir=working_dir,
            phase_params=phase_params,
            refinement_params=refinement_params,
            backend=backend,
            backend_options=backend_options,
            show_progress=show_progress,
        )
