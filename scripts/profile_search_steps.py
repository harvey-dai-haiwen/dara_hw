from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

import ray
from pymatgen.core import Composition

THREAD_ENV_VARS = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_MAX_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "POLARS_MAX_THREADS",
)


@dataclass
class StepStat:
    name: str
    seconds: float = 0.0
    calls: int = 0
    work: dict[str, float] = field(default_factory=lambda: defaultdict(float))

    def add(self, seconds: float, **work: float) -> None:
        self.seconds += seconds
        self.calls += 1
        for key, value in work.items():
            self.work[key] += float(value)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "step": self.name,
            "seconds": round(self.seconds, 6),
            "calls": self.calls,
        }
        if self.work:
            payload["work"] = {key: round(value, 6) for key, value in sorted(self.work.items())}
        return payload


class StepRecorder:
    def __init__(self) -> None:
        self._stats: dict[str, StepStat] = {}

    def add(self, name: str, seconds: float, **work: float) -> None:
        if name not in self._stats:
            self._stats[name] = StepStat(name=name)
        self._stats[name].add(seconds, **work)

    def as_list(self) -> list[dict[str, Any]]:
        return [
            self._stats[name].as_dict()
            for name in sorted(self._stats, key=lambda key: self._stats[key].seconds, reverse=True)
        ]


def configure_threads(threads: int) -> None:
    for variable in THREAD_ENV_VARS:
        os.environ[variable] = str(max(1, threads))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Profile Dara search steps for a concrete sample and precursor set."
    )
    parser.add_argument("--dara-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--sample-path", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--database",
        choices=["COD", "ICSD", "MP", "ALL"],
        default="ALL",
    )
    parser.add_argument("--precursor", action="append", required=True)
    parser.add_argument("--instrument-profile", default="Aeris-fds-Pixcel1d-Medipix3")
    parser.add_argument("--wavelength", default="Cu")
    parser.add_argument("--max-phases", type=int, default=3)
    parser.add_argument(
        "--threads",
        type=int,
        default=1,
        help="Thread cap for Python/native libraries controlled through environment variables.",
    )
    parser.add_argument(
        "--bgmn-threads",
        type=int,
        default=4,
        help="Thread count passed to Dara refinement (BGMN).",
    )
    parser.add_argument(
        "--max-parallel-jobs",
        type=int,
        default=1,
        help="Maximum concurrent Ray search jobs.",
    )
    parser.add_argument(
        "--resource-profile",
        choices=["auto", "small", "medium", "large"],
        default="auto",
        help="Resource profile used by Dara search, Ray, and peak matching.",
    )
    parser.add_argument("--memory-gb", type=float, default=None)
    parser.add_argument("--peak-match-chunk-size", type=int, default=None)
    parser.add_argument("--peak-match-batch-size", type=int, default=None)
    parser.add_argument("--peak-match-max-pending-batches", type=int, default=None)
    parser.add_argument("--ray-object-store-memory-gb", type=float, default=None)
    parser.add_argument(
        "--ray-mode",
        choices=["local", "cluster"],
        default="local",
        help="Use local mode for deterministic per-step attribution, or cluster for standard Ray execution.",
    )
    parser.add_argument("--keep-artifacts", action="store_true")
    parser.add_argument("--output-path", type=Path, default=None)
    return parser


def build_databases(database_name: str, dara_root: Path):
    from dara.structure_db import CODDatabase, ICSDDatabase, MPDatabase

    database_map = {
        "COD": [CODDatabase(dara_root / "cod_cifs")],
        "ICSD": [ICSDDatabase(dara_root / "icsd_cifs")],
        "MP": [MPDatabase(dara_root / "mp_cifs")],
        "ALL": [
            CODDatabase(dara_root / "cod_cifs"),
            ICSDDatabase(dara_root / "icsd_cifs"),
            MPDatabase(dara_root / "mp_cifs"),
        ],
    }
    return database_map[database_name]


def compute_chemsys(precursors: list[str]) -> set[str]:
    elements: set[str] = set()
    for precursor in precursors:
        elements.update(str(element) for element in Composition(precursor).elements)
    return elements


def patch_search_steps(recorder: StepRecorder):
    import dara.search.tree as tree_module
    from dara import do_refinement_no_saving
    from dara.cif2str import CIF2StrError

    context = {"in_expand_node": 0, "in_initial_cleaning": 0}
    originals: dict[tuple[Any, str], Any] = {}

    def store(owner: Any, attr: str, replacement) -> None:
        originals[(owner, attr)] = getattr(owner, attr)
        setattr(owner, attr, replacement)

    original_detect_peak = tree_module.SearchTree._detect_peak_in_pattern

    def wrapped_detect_peak(self, *args, **kwargs):
        start = time.perf_counter()
        peak_list = original_detect_peak(self, *args, **kwargs)
        recorder.add(
            "detect_peaks",
            time.perf_counter() - start,
            peaks_detected=len(peak_list),
            peaks_kept=len(self.peak_obs),
        )
        return peak_list

    store(tree_module.SearchTree, "_detect_peak_in_pattern", wrapped_detect_peak)

    original_create_root = tree_module.SearchTree._create_root_node

    def wrapped_create_root(self, *args, **kwargs):
        start = time.perf_counter()
        node = original_create_root(self, *args, **kwargs)
        recorder.add(
            "create_root_node",
            time.perf_counter() - start,
            pinned_phases=len(self.pinned_phases),
        )
        return node

    store(tree_module.SearchTree, "_create_root_node", wrapped_create_root)

    original_get_all_cleaned = tree_module.SearchTree._get_all_cleaned_phases_result

    def wrapped_get_all_cleaned(self, *args, **kwargs):
        context["in_initial_cleaning"] += 1
        start = time.perf_counter()
        try:
            results = original_get_all_cleaned(self, *args, **kwargs)
        finally:
            context["in_initial_cleaning"] -= 1
        non_pinned = [phase for phase in self.cif_paths if phase not in set(self.pinned_phases)]
        recorder.add(
            "initial_cleaning",
            time.perf_counter() - start,
            candidate_phases=len(non_pinned),
            surviving_phases=len(results),
            removed_phases=max(0, len(non_pinned) - len(results)),
        )
        return results

    store(tree_module.SearchTree, "_get_all_cleaned_phases_result", wrapped_get_all_cleaned)

    original_refine_phases = tree_module.BaseSearchTree.refine_phases

    def wrapped_refine_phases(self, phases, pinned_phases=None, *args, **kwargs):
        step_name = (
            "initial_single_phase_refinement"
            if context["in_initial_cleaning"]
            else "tree_branch_refinement"
        )
        start = time.perf_counter()
        results = original_refine_phases(self, phases, pinned_phases, *args, **kwargs)
        recorder.add(
            step_name,
            time.perf_counter() - start,
            candidate_branches=len(phases),
            pinned_phases=len(pinned_phases or []),
            successful_refinements=sum(1 for result in results.values() if result is not None),
        )
        return results

    store(tree_module.BaseSearchTree, "refine_phases", wrapped_refine_phases)

    original_group_phases = tree_module.group_phases

    def wrapped_group_phases(all_phases_result, *args, **kwargs):
        step_name = "tree_grouping" if context["in_expand_node"] else "initial_grouping"
        start = time.perf_counter()
        grouped = original_group_phases(all_phases_result, *args, **kwargs)
        valid_groups = {
            metadata["group_id"]
            for metadata in grouped.values()
            if metadata["group_id"] >= 0
        }
        recorder.add(
            step_name,
            time.perf_counter() - start,
            phases_grouped=len(all_phases_result),
            output_groups=len(valid_groups),
        )
        return grouped

    store(tree_module, "group_phases", wrapped_group_phases)

    original_score_phases = tree_module.BaseSearchTree.score_phases

    def wrapped_score_phases(self, all_phases_result, current_result=None, *args, **kwargs):
        start = time.perf_counter()
        best_phases, raw_scores, threshold = original_score_phases(
            self,
            all_phases_result,
            *args,
            current_result=current_result,
            **kwargs,
        )
        recorder.add(
            "score_candidate_phases",
            time.perf_counter() - start,
            candidates_seen=len(all_phases_result),
            candidates_selected=len(best_phases),
            peak_match_threshold=threshold,
        )
        return best_phases, raw_scores, threshold

    store(tree_module.BaseSearchTree, "score_phases", wrapped_score_phases)

    original_expand_node = tree_module.BaseSearchTree.expand_node

    def wrapped_expand_node(self, nid, *args, **kwargs):
        node = self.get_node(nid)
        current_phase_count = len(node.data.current_phases) if node and node.data else 0
        context["in_expand_node"] += 1
        start = time.perf_counter()
        try:
            children = original_expand_node(self, nid, *args, **kwargs)
        finally:
            context["in_expand_node"] -= 1
        recorder.add(
            "expand_search_node",
            time.perf_counter() - start,
            current_phase_count=current_phase_count,
            spawned_children=len(children),
        )
        return children

    store(tree_module.BaseSearchTree, "expand_node", wrapped_expand_node)

    original_get_search_results = tree_module.SearchTree.get_search_results

    def wrapped_get_search_results(self, *args, **kwargs):
        start = time.perf_counter()
        results = original_get_search_results(self, *args, **kwargs)
        recorder.add(
            "collect_search_results",
            time.perf_counter() - start,
            result_count=len(results),
        )
        return results

    store(tree_module.SearchTree, "get_search_results", wrapped_get_search_results)

    def restore() -> None:
        for (owner, attr), original in reversed(list(originals.items())):
            setattr(owner, attr, original)

    def serial_batch_peak_matching(
        peak_calcs,
        peak_obs,
        return_type="PeakMatcher",
        batch_size=100,
        score_kwargs=None,
        max_pending_batches=None,
        resource_budget=None,
    ):
        peak_obs_values = [peak_obs] * len(peak_calcs) if hasattr(peak_obs, "shape") else peak_obs

        results = []
        for peak_calc, peak_obs_item in zip(peak_calcs, peak_obs_values, strict=False):
            peak_matcher = tree_module.PeakMatcher(peak_calc, peak_obs_item)
            if return_type == "PeakMatcher":
                results.append(peak_matcher)
            elif return_type == "score":
                results.append(peak_matcher.score(**(score_kwargs or {})))
            elif return_type == "jaccard":
                results.append(peak_matcher.jaccard_index())
            else:
                raise ValueError(f"Unknown return type {return_type}")
        return results

    store(tree_module, "batch_peak_matching", serial_batch_peak_matching)

    def serial_batch_refinement(
        pattern_path,
        cif_paths,
        wavelength="Cu",
        instrument_profile="Aeris-fds-Pixcel1d-Medipix3",
        phase_params=None,
        refinement_params=None,
        resource_budget=None,
    ):
        results = []
        for references in cif_paths:
            if len(references) == 0:
                results.append(None)
                continue
            try:
                result = do_refinement_no_saving(
                    pattern_path,
                    references,
                    wavelength=wavelength,
                    instrument_profile=instrument_profile,
                    phase_params=phase_params,
                    refinement_params=refinement_params,
                )
            except (RuntimeError, OSError, ValueError, CIF2StrError):
                result = None
            if result is not None and result.lst_data.rpb == 100:
                result = None
            results.append(result)
        return results

    store(tree_module, "batch_refinement", serial_batch_refinement)

    return restore


def extract_top_phases(results) -> list[str]:
    if not results:
        return []

    best_result = results[0]
    phase_names = []
    for phase_options in best_result.phases:
        if not phase_options:
            continue
        phase_names.append(phase_options[0].path.stem)
    return phase_names


def run_profile(args: argparse.Namespace) -> dict[str, Any]:
    sys.path.insert(0, str(args.dara_root / "src"))

    from dara.search.core import search_phases
    from dara.xrd import load_pattern

    recorder = StepRecorder()
    restore = patch_search_steps(recorder)

    sample_path = args.sample_path.resolve()
    label = args.label or sample_path.stem
    chemsys = compute_chemsys(args.precursor)
    cifs_path = Path(mkdtemp(prefix=f"dara-profile-{label}-"))

    db_summaries: list[dict[str, Any]] = []
    copied_cifs = 0

    try:
        pattern_start = time.perf_counter()
        pattern = load_pattern(sample_path)
        recorder.add(
            "load_pattern",
            time.perf_counter() - pattern_start,
            data_points=len(pattern.angles),
        )

        for database in build_databases(args.database, args.dara_root):
            before = {path.name for path in cifs_path.glob("*.cif")}
            start = time.perf_counter()
            database.get_cifs_by_chemsys(chemsys, copy_files=True, dest_dir=cifs_path.as_posix())
            elapsed = time.perf_counter() - start
            after = {path.name for path in cifs_path.glob("*.cif")}
            new_files = len(after - before)
            copied_cifs += new_files
            db_summaries.append(
                {
                    "database": database.__class__.__name__,
                    "seconds": round(elapsed, 6),
                    "new_cifs": new_files,
                }
            )
            recorder.add(
                f"copy_{database.__class__.__name__}",
                elapsed,
                new_cifs=new_files,
            )

        all_cifs = sorted(cifs_path.glob("*.cif"))
        if not all_cifs:
            raise ValueError(f"No CIFs copied for chemical system {sorted(chemsys)}")

        from dara.resources import DaraResourceBudget, init_ray_for_dara

        ray.shutdown()
        resource_budget = DaraResourceBudget(
            profile=args.resource_profile,
            total_cpus=args.max_parallel_jobs * args.bgmn_threads,
            memory_gb=args.memory_gb,
            bgmn_threads=args.bgmn_threads,
            max_bgmn_tasks=args.max_parallel_jobs,
            native_threads=args.threads,
            peak_match_chunk_size=args.peak_match_chunk_size,
            peak_match_batch_size=args.peak_match_batch_size,
            peak_match_max_pending_batches=args.peak_match_max_pending_batches,
            ray_object_store_memory_gb=args.ray_object_store_memory_gb,
            ray_local_mode=args.ray_mode == "local",
        ).resolve()
        init_ray_for_dara(resource_budget)

        overall_start = time.perf_counter()
        results = search_phases(
            pattern_path=sample_path,
            phases=all_cifs,
            wavelength=args.wavelength,
            instrument_profile=args.instrument_profile,
            max_phases=args.max_phases,
            express_mode=True,
            enable_angular_cut=True,
            refinement_params={"n_threads": args.bgmn_threads},
            resource_budget=resource_budget,
        )
        total_elapsed = time.perf_counter() - overall_start
    finally:
        restore()
        ray.shutdown()
        if not args.keep_artifacts:
            shutil.rmtree(cifs_path, ignore_errors=True)

    best_rwp = results[0].refinement_result.lst_data.rwp if results else None
    return {
        "label": label,
        "sample_path": sample_path.as_posix(),
        "database": args.database,
        "precursors": args.precursor,
        "chemical_system": sorted(chemsys),
        "instrument_profile": args.instrument_profile,
        "wavelength": args.wavelength,
        "threads": args.threads,
        "bgmn_threads": args.bgmn_threads,
        "max_parallel_jobs": args.max_parallel_jobs,
        "ray_mode": args.ray_mode,
        "resource_budget": asdict(resource_budget),
        "candidate_cifs": len(all_cifs),
        "copied_cifs": copied_cifs,
        "database_copy_breakdown": db_summaries,
        "total_search_seconds": round(total_elapsed, 6),
        "best_rwp": None if best_rwp is None else round(best_rwp, 6),
        "result_count": len(results),
        "top_phases": extract_top_phases(results),
        "steps": recorder.as_list(),
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.dara_root = args.dara_root.resolve()
    if args.threads < 1 or args.bgmn_threads < 1 or args.max_parallel_jobs < 1:
        raise ValueError("threads, bgmn-threads, and max-parallel-jobs must all be >= 1")
    configure_threads(args.threads)
    summary = run_profile(args)
    if args.output_path is not None:
        args.output_path.parent.mkdir(parents=True, exist_ok=True)
        args.output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
