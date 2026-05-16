"""Automatically configures DARA settings."""

from importlib.metadata import version

from dara.refine import RefinementPhase, do_refinement, do_refinement_no_saving
from dara.search_match import DaraSearchMatchConfig, ElementFilterConfig, ExternalCsvConfig, MachineConfig, run_search_match
from dara.settings import DaraSettings

__version__ = version("dara-xrd")
SETTINGS = DaraSettings()


def __getattr__(name: str):
    if name == "search_phases":
        from dara.search import search_phases

        return search_phases
    raise AttributeError(f"module 'dara' has no attribute {name!r}")


__all__ = [
    "RefinementPhase",
    "DaraSearchMatchConfig",
    "ElementFilterConfig",
    "ExternalCsvConfig",
    "MachineConfig",
    "do_refinement",
    "do_refinement_no_saving",
    "run_search_match",
    "search_phases",
    "DaraSettings",
    "SETTINGS",
]
