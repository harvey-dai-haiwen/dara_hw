"""High-level search-match workflow for programmatic and CLI use."""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Literal


DATABASE_NAMES = ("ICSD", "COD", "MP")


def slugify(text: str) -> str:
    """Return a filesystem-safe slug."""
    lowered = text.lower().strip()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "sample"


def _resolve_path(base: Path, raw_path: str | Path) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else base / path


@dataclass(frozen=True)
class MachineConfig:
    """Machine and CPU target used to build a Dara resource budget."""

    physical_cores: int | None = None
    logical_threads: int | None = None
    memory_gb: float | None = None
    cpu_target_fraction: float = 0.75
    target_cpus: int | None = None
    resource_profile: Literal["auto", "small", "medium", "large"] = "auto"
    native_threads: int = 8
    bgmn_threads: int = 2
    max_parallel_jobs: int = 8
    peak_match_chunk_size: int | None = None
    peak_match_batch_size: int | None = None
    peak_match_max_pending_batches: int | None = None
    ray_object_store_memory_gb: float | None = None
    ray_local_mode: bool = False

    def resolved_target_cpus(self) -> int:
        """Return target CPU count from explicit target or logical CPU fraction."""
        if self.target_cpus is not None:
            return max(1, int(self.target_cpus))
        if self.logical_threads is not None:
            return max(1, int(self.logical_threads * self.cpu_target_fraction))
        return max(1, self.bgmn_threads * (self.max_parallel_jobs or 1))

    def resolved_max_parallel_jobs(self) -> int:
        """Return concurrent refinement task count."""
        if self.max_parallel_jobs is not None:
            return max(1, int(self.max_parallel_jobs))
        return max(1, self.resolved_target_cpus() // max(1, int(self.bgmn_threads)))


@dataclass(frozen=True)
class ElementFilterConfig:
    """Three-group chemistry filter for candidate CIF selection."""

    must: tuple[str, ...] = ()
    any: tuple[str, ...] = ()
    any_expression: str | None = None
    possible: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExternalCsvConfig:
    """External CSV containing one CIF text column."""

    path: Path
    cif_column: str | None = None
    symprec: float = 0.1
    angle_tolerance: float = 5.0
    limit: int | None = None


@dataclass(frozen=True)
class DaraSearchMatchConfig:
    """Configuration for a complete Dara search-match workflow."""

    sample_path: Path
    output_root: Path | None = None
    dara_root: Path | None = None
    databases: tuple[Literal["ICSD", "COD", "MP"], ...] = ("ICSD",)
    precursors: tuple[str, ...] = ()
    element_filter: ElementFilterConfig = field(default_factory=ElementFilterConfig)
    additional_cifs: tuple[Path, ...] = ()
    pinned_cifs: tuple[Path, ...] = ()
    additional_cif_dirs: tuple[Path, ...] = ()
    external_csvs: tuple[ExternalCsvConfig, ...] = ()
    disable_structure_dedupe: bool = False
    instrument_profile: str | Path = "Aeris-fds-Pixcel1d-Medipix3"
    wavelength: str | float = "Cu"
    max_phases: int = 4
    max_results: int = 1000
    refinement_backend: Literal["bgmn", "gsas", "fullprof"] | str = "bgmn"
    backend_options: dict[str, Any] = field(default_factory=dict)
    machine: MachineConfig = field(default_factory=MachineConfig)
    dry_run: bool = False
    keep_work: bool = False
    skip_refinement_export: bool = False


def build_database_objects(names: Iterable[str], dara_root: Path):
    """Instantiate local Dara database mirrors."""
    from dara.settings import DaraSettings
    from dara.structure_db import CODDatabase, ICSDDatabase, MPDatabase

    normalized = [name.upper() for name in names]
    unknown = sorted(set(normalized) - set(DATABASE_NAMES))
    if unknown:
        raise ValueError(f"Unknown database name(s): {', '.join(unknown)}")
    settings = DaraSettings()
    db_map = {
        "ICSD": ICSDDatabase(settings.PATH_TO_ICSD),
        "COD": CODDatabase(settings.PATH_TO_COD),
        "MP": MPDatabase(settings.PATH_TO_MP),
    }
    return [db_map[name] for name in normalized]


def collect_additional_cifs(config: DaraSearchMatchConfig, dara_root: Path) -> list[Path]:
    """Collect user-provided CIF files and directories."""
    paths = [_resolve_path(dara_root, raw_path).resolve() for raw_path in config.additional_cifs]
    for raw_dir in config.additional_cif_dirs:
        directory = _resolve_path(dara_root, raw_dir).resolve()
        if not directory.exists():
            raise FileNotFoundError(f"Additional CIF directory does not exist: {directory}")
        paths.extend(sorted(path.resolve() for path in directory.glob("*.cif")))

    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = path.as_posix().lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def collect_pinned_cifs(config: DaraSearchMatchConfig, dara_root: Path) -> list[Path]:
    """Collect user-provided CIF files that must appear in every solution."""
    paths = [_resolve_path(dara_root, raw_path).resolve() for raw_path in config.pinned_cifs]
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Pinned CIF does not exist: {path}")
        key = path.as_posix().lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def remove_searchable_duplicates_of_pinned(
    pinned_paths: Iterable[Path | str],
    searchable_paths: Iterable[Path | str],
) -> tuple[list[Path], list[dict[str, str]], list[dict[str, str]]]:
    """Remove ordinary candidates that duplicate pinned phases only."""
    from pymatgen.analysis.structure_matcher import StructureMatcher
    from pymatgen.core import Structure

    matcher = StructureMatcher()
    parse_failures: list[dict[str, str]] = []
    pinned_structures: list[tuple[Path, Any]] = []
    for raw_path in pinned_paths:
        path = Path(raw_path)
        try:
            pinned_structures.append((path, Structure.from_file(path)))
        except Exception as exc:
            parse_failures.append({"path": path.as_posix(), "source": "pinned", "error": str(exc)})

    kept: list[Path] = []
    duplicates: list[dict[str, str]] = []
    for raw_path in searchable_paths:
        path = Path(raw_path)
        try:
            structure = Structure.from_file(path)
        except Exception as exc:
            parse_failures.append({"path": path.as_posix(), "source": "searchable", "error": str(exc)})
            continue

        match = next(
            (
                pinned_path
                for pinned_path, pinned_structure in pinned_structures
                if matcher.fit(pinned_structure, structure)
            ),
            None,
        )
        if match is None:
            kept.append(path)
        else:
            duplicates.append(
                {
                    "searchable_path": path.as_posix(),
                    "pinned_path": match.as_posix(),
                }
            )
    return kept, duplicates, parse_failures


def merge_rejected_counts(*counts: dict[str, int]) -> dict[str, int]:
    """Merge candidate rejection counters."""
    merged: dict[str, int] = {}
    for item in counts:
        for key, value in item.items():
            merged[key] = merged.get(key, 0) + int(value)
    return merged


def _phase_name(phase: Any) -> str:
    path = getattr(phase, "path", None)
    if path is not None:
        return Path(path).stem
    return str(phase)


def summarize_results(results: list[Any], max_results: int) -> list[dict[str, Any]]:
    """Summarize search results without serializing large in-memory objects."""
    summaries: list[dict[str, Any]] = []
    for rank, result in enumerate(results[:max_results], start=1):
        refinement = result.refinement_result
        summaries.append(
            {
                "rank": rank,
                "rwp": round(float(refinement.lst_data.rwp), 6),
                "phases": [[_phase_name(phase) for phase in group] for group in result.phases],
            }
        )
    return summaries


def extract_refinement_phases(refinement_result: Any) -> list[dict[str, Any]]:
    """Return normalized phase fractions and phase metadata."""
    weights = refinement_result.get_phase_weights(normalize=True)
    rows: list[dict[str, Any]] = []
    for phase_name, phase_result in refinement_result.lst_data.phases_results.items():
        rows.append(
            {
                "phase": phase_name,
                "weight_fraction": float(weights.get(phase_name, 0.0)),
                "weight_percent": float(weights.get(phase_name, 0.0)) * 100.0,
                "rphase": phase_result.rphase,
                "spacegroup_no": phase_result.spacegroup_no,
                "hermann_mauguin": phase_result.hermann_mauguin,
            }
        )
    rows.sort(key=lambda item: item["weight_fraction"], reverse=True)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write dict rows as CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def export_refinement_artifacts(results: list[Any], output_root: Path, max_results: int) -> list[dict[str, Any]]:
    """Write per-rank refinement plots and phase fractions."""
    exports: list[dict[str, Any]] = []
    export_root = output_root / "searchmatch"
    for rank, result in enumerate(results[:max_results], start=1):
        refinement = result.refinement_result
        rank_dir = export_root / f"rank_{rank:03d}"
        rank_dir.mkdir(parents=True, exist_ok=True)
        plot_path = rank_dir / "refinement_plot.html"
        phase_csv = rank_dir / "phase_fractions.csv"
        phase_json = rank_dir / "phase_fractions.json"
        summary_path = rank_dir / "refinement_summary.json"
        phase_rows = extract_refinement_phases(refinement)
        refinement.visualize(diff_offset=True).write_html(plot_path.as_posix())
        write_csv(phase_csv, phase_rows)
        phase_json.write_text(json.dumps(phase_rows, indent=2), encoding="utf-8")
        payload = {
            "rank": rank,
            "rwp": float(refinement.lst_data.rwp),
            "rp": float(refinement.lst_data.rp),
            "rpb": float(refinement.lst_data.rpb),
            "rho": float(refinement.lst_data.rho),
            "plot": plot_path.as_posix(),
            "phase_fractions_csv": phase_csv.as_posix(),
            "phase_fractions_json": phase_json.as_posix(),
            "phases": phase_rows,
        }
        summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        exports.append({**payload, "summary": summary_path.as_posix()})
    return exports


def _resource_budget_from_config(config: DaraSearchMatchConfig):
    from dara.resources import DaraResourceBudget

    machine = config.machine
    target_cpus = machine.resolved_target_cpus()
    max_parallel_jobs = machine.resolved_max_parallel_jobs()
    peak_match_chunk_size = machine.peak_match_chunk_size
    peak_match_max_pending_batches = machine.peak_match_max_pending_batches
    if peak_match_chunk_size is None:
        peak_match_chunk_size = 50_000 if target_cpus >= 16 else 10_000
    if peak_match_max_pending_batches is None:
        peak_match_max_pending_batches = max(1, min(32, max_parallel_jobs * 2))

    return DaraResourceBudget(
        profile=machine.resource_profile,
        total_cpus=target_cpus,
        memory_gb=machine.memory_gb,
        bgmn_threads=machine.bgmn_threads,
        max_bgmn_tasks=max_parallel_jobs,
        native_threads=machine.native_threads,
        peak_match_chunk_size=peak_match_chunk_size,
        peak_match_batch_size=machine.peak_match_batch_size,
        peak_match_max_pending_batches=peak_match_max_pending_batches,
        ray_object_store_memory_gb=machine.ray_object_store_memory_gb,
        ray_local_mode=machine.ray_local_mode,
    ).resolve()


def _prepare_candidates(
    config: DaraSearchMatchConfig,
    dara_root: Path,
    output_root: Path,
    database_objects: Iterable[Any] | None,
) -> tuple[list[Path], list[Path], dict[str, Any]]:
    from dara.candidate_filter import CandidateElementFilter, collect_database_cifs, copy_selected_cifs, filter_cif_paths
    from dara.external_candidates import deduplicate_external_cifs, prepare_external_cifs_from_csv

    element_filter = CandidateElementFilter(
        must_elements=config.element_filter.must,
        any_elements=config.element_filter.any,
        any_expression=config.element_filter.any_expression,
        possible_elements=config.element_filter.possible,
    )
    if not (
        element_filter.query_elements
        or config.additional_cifs
        or config.pinned_cifs
        or config.additional_cif_dirs
        or config.external_csvs
    ):
        raise ValueError("Provide element filters or additional CIFs before running Dara search.")

    candidate_raw_dir = output_root / "candidates" / "raw"
    selected_dir = output_root / "candidates" / "selected"
    databases = list(database_objects) if database_objects is not None else build_database_objects(config.databases, dara_root)

    database_candidate_paths: list[Path] = []
    if element_filter.query_elements and databases:
        database_candidate_paths.extend(
            collect_database_cifs(
                databases,
                element_filter,
                candidate_raw_dir,
            )
        )

    external_manifests = []
    external_candidate_paths = collect_additional_cifs(config, dara_root)
    external_csv_dir = output_root / "preprocessing" / "external-cifs"
    for external_csv in config.external_csvs:
        csv_path = _resolve_path(dara_root, external_csv.path).resolve()
        external_result = prepare_external_cifs_from_csv(
            csv_path,
            external_csv_dir / slugify(csv_path.stem),
            cif_column=external_csv.cif_column,
            symprec=external_csv.symprec,
            angle_tolerance=external_csv.angle_tolerance,
            limit=external_csv.limit,
        )
        external_manifests.append(external_result.manifest)
        external_candidate_paths.extend(external_result.cif_paths)

    database_selection = filter_cif_paths(database_candidate_paths, element_filter)
    external_selection = filter_cif_paths(external_candidate_paths, element_filter)
    pinned_input_paths = collect_pinned_cifs(config, dara_root)
    pinned_selection = filter_cif_paths(pinned_input_paths, element_filter)
    if len(pinned_selection.selected_paths) != len(pinned_input_paths):
        raise ValueError(
            "One or more pinned CIFs could not be parsed or did not satisfy the element filter."
        )

    dedupe_result = None
    selected_external_paths = external_selection.selected_paths
    if not config.disable_structure_dedupe:
        dedupe_result = deduplicate_external_cifs(database_selection.selected_paths, selected_external_paths)
        selected_external_paths = dedupe_result.kept_external_paths

    searchable_paths = [*database_selection.selected_paths, *selected_external_paths]
    pinned_searchable_duplicates: list[dict[str, str]] = []
    pinned_searchable_parse_failures: list[dict[str, str]] = []
    if pinned_selection.selected_paths and searchable_paths:
        (
            searchable_paths,
            pinned_searchable_duplicates,
            pinned_searchable_parse_failures,
        ) = remove_searchable_duplicates_of_pinned(
            pinned_selection.selected_paths,
            searchable_paths,
        )

    selected_paths = copy_selected_cifs(
        [*searchable_paths, *pinned_selection.selected_paths],
        selected_dir,
    )
    pinned_count = len(pinned_selection.selected_paths)
    selected_searchable_paths = selected_paths[: len(searchable_paths)]
    selected_pinned_paths = selected_paths[len(searchable_paths) :]
    selected_metadata = [{**item, "source": "database"} for item in database_selection.selected_metadata]
    external_kept_set = {path.resolve() for path in selected_external_paths}
    selected_metadata.extend(
        {**item, "source": "external"}
        for item in external_selection.selected_metadata
        if Path(item["path"]).resolve() in external_kept_set
    )
    searchable_kept_set = {path.resolve() for path in searchable_paths}
    selected_metadata = [
        item for item in selected_metadata if Path(item["path"]).resolve() in searchable_kept_set
    ]
    selected_metadata.extend(
        {**item, "source": "pinned"}
        for item in pinned_selection.selected_metadata
    )

    candidate_summary = {
        "databases": list(config.databases),
        "precursors": list(config.precursors),
        "element_filter": element_filter.as_dict(),
        "pinned_cifs": [path.as_posix() for path in pinned_input_paths],
        "pinned_selected_paths": [path.as_posix() for path in selected_pinned_paths],
        "pinned_count": pinned_count,
        "candidate_count_raw": len(database_candidate_paths) + len(external_candidate_paths) + len(pinned_input_paths),
        "candidate_count_database_raw": len(database_candidate_paths),
        "candidate_count_external_raw": len(external_candidate_paths),
        "candidate_count_pinned_raw": len(pinned_input_paths),
        "candidate_count_database_selected": len(database_selection.selected_paths),
        "candidate_count_external_selected_before_dedupe": len(external_selection.selected_paths),
        "candidate_count_external_selected": len(selected_external_paths),
        "candidate_count_pinned_selected": pinned_count,
        "candidate_count_searchable_selected": len(selected_searchable_paths),
        "candidate_count_selected": len(selected_paths),
        "rejected_counts": merge_rejected_counts(
            database_selection.rejected_counts,
            external_selection.rejected_counts,
            pinned_selection.rejected_counts,
        ),
        "selected_cifs": selected_metadata,
        "external_manifests": external_manifests,
        "structure_dedupe": {
            "enabled": not config.disable_structure_dedupe,
            "external_duplicate_count": len(dedupe_result.duplicates) if dedupe_result else 0,
            "searchable_duplicate_of_pinned_count": len(pinned_searchable_duplicates),
            "parse_failures": [
                *(dedupe_result.parse_failures if dedupe_result else []),
                *pinned_searchable_parse_failures,
            ],
            "external_duplicates": [
                {
                    "external_path": duplicate.external_path.as_posix(),
                    "matched_path": duplicate.matched_path.as_posix(),
                    "matched_source": duplicate.matched_source,
                }
                for duplicate in (dedupe_result.duplicates if dedupe_result else [])
            ],
            "searchable_duplicates_of_pinned": pinned_searchable_duplicates,
        },
    }
    return selected_searchable_paths, selected_pinned_paths, candidate_summary


def run_search_match(
    config: DaraSearchMatchConfig,
    *,
    database_objects: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """Run candidate selection, Dara search-match, and artifact export.

    ``database_objects`` is mainly for tests or custom callers that want to
    provide database-like objects with ``get_cifs_by_chemsys``.
    """
    dara_root = (config.dara_root or Path.cwd()).resolve()
    sample_path = _resolve_path(dara_root, config.sample_path).resolve()
    if len(config.pinned_cifs) >= config.max_phases:
        raise ValueError("The number of pinned CIFs must be less than max_phases because pinned phases are counted.")
    output_root = config.output_root
    if output_root is None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_root = sample_path.parent / "metadata" / "dara" / f"{stamp}-{slugify(sample_path.stem)}"
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    resource_budget = _resource_budget_from_config(config)
    selected_paths, pinned_paths, candidate_summary = _prepare_candidates(config, dara_root, output_root, database_objects)

    summary: dict[str, Any] = {
        "status": "planned" if config.dry_run else "running",
        "sample_path": sample_path.as_posix(),
        "output_root": output_root.as_posix(),
        "machine": {
            "physical_cores": config.machine.physical_cores,
            "logical_threads": config.machine.logical_threads,
            "memory_gb": config.machine.memory_gb,
            "cpu_target_fraction": config.machine.cpu_target_fraction,
            "target_cpus": config.machine.resolved_target_cpus(),
        },
        "resource_budget": asdict(resource_budget),
        "instrument_profile": str(config.instrument_profile),
        "wavelength": config.wavelength,
        "max_phases": config.max_phases,
        "max_results": config.max_results,
        "refinement_backend": config.refinement_backend,
        "backend_options": config.backend_options,
        **candidate_summary,
    }

    if config.dry_run:
        (output_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    if not selected_paths:
        summary["status"] = "error"
        summary["error"] = "No CIF candidates passed the element filter."
        (output_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    import ray

    from dara.search import search_phases

    work_dir = output_root / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    old_cwd = Path.cwd()
    try:
        os.chdir(work_dir)
        results = search_phases(
            pattern_path=sample_path,
            phases=selected_paths,
            pinned_phases=pinned_paths,
            max_phases=config.max_phases,
            wavelength=config.wavelength,  # type: ignore[arg-type]
            instrument_profile=config.instrument_profile,
            express_mode=True,
            enable_angular_cut=True,
            refinement_params={"n_threads": config.machine.bgmn_threads},
            resource_budget=resource_budget,
            refinement_backend=config.refinement_backend,
            backend_options=config.backend_options,
        )
    finally:
        os.chdir(old_cwd)
        ray.shutdown()

    result_summaries = summarize_results(results, config.max_results)
    summary["status"] = "ok"
    summary["result_count"] = len(results)
    summary["best_rwp"] = result_summaries[0]["rwp"] if result_summaries else None
    summary["best_phases"] = result_summaries[0]["phases"] if result_summaries else []
    summary["results"] = result_summaries
    if not config.skip_refinement_export:
        summary["refinement_exports"] = export_refinement_artifacts(results, output_root, config.max_results)
    (output_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if not config.keep_work:
        shutil.rmtree(work_dir, ignore_errors=True)
    return summary
