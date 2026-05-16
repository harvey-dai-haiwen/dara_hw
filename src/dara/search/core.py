"""Phase search module."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Any, Literal

from dara.resources import DaraResourceBudget, init_ray_for_dara
from dara.search.data_model import PeakMatchingStrategy
from dara.search.tree import SearchTree

if TYPE_CHECKING:
    from pathlib import Path

    from dara.refine import RefinementPhase
    from dara.search.data_model import SearchResult

DEFAULT_PHASE_PARAMS = {
    "gewicht": "0_0",
    "lattice_range": 0.01,
    "k1": "0_0^0.01",
    "k2": "fixed",
    "b1": "0_0^0.005",
    "rp": 4,
}
DEFAULT_REFINEMENT_PARAMS = {"eps1": 0, "eps2": "0_-0.05^0.05"}
DEFAULT_PEAK_MATCHING_STRATEGY = PeakMatchingStrategy.default()


def search_phases(
    pattern_path: Path | str,
    phases: list[Path | str | RefinementPhase],
    pinned_phases: list[Path | str | RefinementPhase] | None = None,
    max_phases: int = 5,
    wavelength: Literal["Cu", "Co", "Cr", "Fe", "Mo"] | float = "Cu",
    instrument_profile: str | Path = "Aeris-fds-Pixcel1d-Medipix3",
    express_mode: bool = True,
    enable_angular_cut: bool = True,
    phase_params: dict[str, ...] | None = None,
    refinement_params: dict[str, ...] | None = None,
    return_search_tree: bool = False,
    record_peak_matcher_scores: bool = False,
    rpb_threshold: float | None = None,
    peak_matching_strategy: PeakMatchingStrategy
    | tuple[float, float, float, float] = DEFAULT_PEAK_MATCHING_STRATEGY,
    resource_budget: DaraResourceBudget | dict | None = None,
    refinement_backend: Literal["bgmn", "gsas", "fullprof"] | str = "bgmn",
    backend_options: dict[str, Any] | None = None,
) -> list[SearchResult] | SearchTree:
    """
    Search for the best phases to use for refinement.

    Args:
        pattern_path: the path to the pattern file. It has to be in `.xrdml`, `.xy`, `.raw`, or `.rasx` format
        phases: the paths to the CIF files
        pinned_phases: the paths to the pinned phases, which will be included in all the results
        max_phases: the maximum number of phases to refine
        wavelength: the wavelength of the X-ray. It can be either a float or one of the following strings:
            "Cu", "Co", "Cr", "Fe", "Mo", indicating the material of the X-ray source
        instrument_profile: the name of the instrument, or the path to the instrument configuration file (.geq)
        express_mode: whether to use express mode. In express mode, the phases will be grouped first before
            searching, which can significantly speed up the search process.
        enable_angular_cut: whether to enable angular cut, which will run the search on a reduced pattern range
            (wmin, wmax) to speed up the search process.
        phase_params: the parameters for the phase search
        refinement_params: the parameters for the refinement
        return_search_tree: whether to return the search tree. This is mainly used for debugging purposes.
        record_peak_matcher_scores: whether to record the peak matcher scores. This is mainly used for
            debugging purposes.
        rpb_threshold: the RPB threshold. If None, it will be automatically determined based on the pattern's SNR.
        peak_matching_strategy: the coefficients for peak matching score calculation. Can be a
            PeakMatchingStrategy model or a tuple of four floats
            (matched_coeff, wrong_intensity_coeff, missing_coeff, extra_coeff).
            If None, the default coefficients will be used.
        resource_budget: CPU and memory settings for Ray, BGMN, and peak matching.
        refinement_backend: refinement backend used for search-tree confirmation.
        backend_options: backend-specific options such as GSAS-II instprm or FullProf root.
    """
    if not isinstance(peak_matching_strategy, PeakMatchingStrategy):
        peak_matching_strategy = PeakMatchingStrategy.from_tuple(peak_matching_strategy)

    if phase_params is None:
        phase_params = {}

    if refinement_params is None:
        refinement_params = {}

    resolved_budget = init_ray_for_dara(resource_budget)

    phase_params = {**DEFAULT_PHASE_PARAMS, **phase_params}
    refinement_params = {**DEFAULT_REFINEMENT_PARAMS, **refinement_params}
    refinement_params.setdefault("n_threads", resolved_budget.bgmn_threads)

    # build the search tree
    search_tree = SearchTree(
        pattern_path=pattern_path,
        cif_paths=phases,
        pinned_phases=pinned_phases,
        refine_params=refinement_params,
        phase_params=phase_params,
        wavelength=wavelength,
        instrument_profile=instrument_profile,
        express_mode=express_mode,
        enable_angular_cut=enable_angular_cut,
        max_phases=max_phases,
        rpb_threshold=rpb_threshold,
        record_peak_matcher_scores=record_peak_matcher_scores,
        peak_matching_strategy=peak_matching_strategy,
        resource_budget=resolved_budget,
        refinement_backend=refinement_backend,
        backend_options=backend_options,
    )

    to_be_expanded = deque([search_tree.root])
    while to_be_expanded:
        nid = to_be_expanded.popleft()
        search_tree.expand_node(nid)
        to_be_expanded.extend(search_tree.get_expandable_children(nid))

    if not return_search_tree:
        return search_tree.get_search_results()
    return search_tree
