from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import numpy as np

THREAD_ENV_VARS = (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
    "TBB_NUM_THREADS",
)

DEFAULT_DATABASES = ("COD", "ICSD", "COMBINED")
DEFAULT_PRECURSORS = ("VO2", "ZnO")


def configure_threads(threads: int) -> None:
    for variable in THREAD_ENV_VARS:
        os.environ[variable] = str(max(1, threads))


def slugify(text: str) -> str:
    lowered = text.lower().strip()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "custom-sample"


def resolve_path(base: Path, raw_path: str | Path) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else (base / path)


def unique_paths(paths: list[Path]) -> list[Path]:
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        resolved = path.resolve()
        normalized = resolved.as_posix().lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(resolved)
    return unique


def extract_manifest_cif_paths(payload: object, manifest_path: Path) -> list[Path]:
    if isinstance(payload, list):
        paths: list[Path] = []
        for item in payload:
            if isinstance(item, str) and item.lower().endswith(".cif"):
                paths.append(resolve_path(manifest_path.parent, item))
        return paths

    if not isinstance(payload, dict):
        return []

    generated = payload.get("generated_cifs")
    if isinstance(generated, list):
        paths = []
        for item in generated:
            if not isinstance(item, dict):
                continue
            raw_path = item.get("cif_path")
            if isinstance(raw_path, str) and raw_path.lower().endswith(".cif"):
                paths.append(resolve_path(manifest_path.parent, raw_path))
        return paths

    return []


def collect_additional_cif_paths(args: argparse.Namespace) -> list[Path]:
    paths = [resolve_path(args.dara_root, raw_path) for raw_path in args.additional_cif]

    for raw_dir in args.additional_cif_dir:
        cif_dir = resolve_path(args.dara_root, raw_dir)
        if not cif_dir.exists():
            raise FileNotFoundError(f"Additional CIF directory does not exist: {cif_dir}")
        paths.extend(sorted(cif_dir.glob("*.cif")))

    for raw_manifest in args.additional_cif_manifest:
        manifest_path = resolve_path(args.dara_root, raw_manifest)
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        paths.extend(extract_manifest_cif_paths(payload, manifest_path))

    return unique_paths(paths)


def build_default_output_root(sample_path: Path, run_timestamp: str, engine_name: str = "dara") -> Path:
    sample_slug = slugify(sample_path.stem)
    return sample_path.parent / "metadata" / engine_name / f"{run_timestamp}-{sample_slug}"


def find_or_create_batch(metadata_root: Path, batch_id: str | None = None) -> tuple[str, Path]:
    """Find or create a batch directory.

    Args:
        metadata_root: metadata/dara root directory
        batch_id: explicit batch ID (e.g., "batch_001"). If None, auto-detect or create new.

    Returns:
        tuple of (batch_id, batch_path)
    """
    if batch_id:
        batch_dir = metadata_root / batch_id
    else:
        batch_dirs = sorted([d for d in metadata_root.iterdir() if d.is_dir() and d.name.startswith("batch_")])
        if batch_dirs:
            batch_dir = batch_dirs[-1]
            batch_id = batch_dir.name
        else:
            batch_id = "batch_001"
            batch_dir = metadata_root / batch_id

    batch_dir.mkdir(parents=True, exist_ok=True)
    return batch_id, batch_dir


def build_batch_sample_output_root(batch_dir: Path, sample_path: Path) -> Path:
    """Build output root for a sample within a batch."""
    sample_slug = slugify(sample_path.stem)
    return batch_dir / "samples" / sample_slug


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=json_fallback), encoding="utf-8")


def json_fallback(value):
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (set, tuple)):
        return list(value)
    return str(value)


def remove_tree_with_retries(path: Path, retries: int = 6, delay_seconds: float = 0.5) -> None:
    for attempt in range(retries):
        try:
            shutil.rmtree(path)
            return
        except PermissionError:
            if attempt == retries - 1:
                raise
            time.sleep(delay_seconds)


def copy_sample(sample_path: Path, output_root: Path) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    staged_path = output_root / sample_path.name
    shutil.copy2(sample_path, staged_path)
    return staged_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark a custom XRD sample with Dara's original PhaseSearchMaker interface."
    )
    parser.add_argument("--dara-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--sample-path", type=Path, required=True)
    parser.add_argument(
        "--database",
        nargs="+",
        choices=["COD", "ICSD", "MP", "ALL", "COMBINED"],
        default=list(DEFAULT_DATABASES),
    )
    parser.add_argument("--precursor", action="append", default=[])
    parser.add_argument("--additional-cif", action="append", default=[])
    parser.add_argument(
        "--additional-cif-dir",
        action="append",
        default=[],
        help="Repeat for each directory containing additional CIF files to include.",
    )
    parser.add_argument(
        "--additional-cif-manifest",
        action="append",
        default=[],
        help="Repeat for each JSON manifest that lists generated external CIF files.",
    )
    parser.add_argument("--instrument-profile", default="Aeris-fds-Pixcel1d-Medipix3")
    parser.add_argument("--wavelength", default="Cu")
    parser.add_argument("--max-phases", type=int, default=4)
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--bgmn-threads", type=int, default=4)
    parser.add_argument("--max-parallel-jobs", type=int, default=2)
    parser.add_argument(
        "--refinement-backend",
        choices=["bgmn", "gsas", "fullprof"],
        default="bgmn",
        help="Refinement backend for Dara search confirmation. Default: bgmn.",
    )
    parser.add_argument(
        "--compare-refinement-backends",
        default="",
        help="Comma-separated backends to run into separate folders, e.g. bgmn,gsas,fullprof.",
    )
    parser.add_argument("--gsas-instprm", type=Path, default=None)
    parser.add_argument(
        "--gsas-conda-env",
        default="GSASII_fix",
        help="Conda env used for GSAS-II external worker. Use an empty string to run GSAS-II in the current env.",
    )
    parser.add_argument("--fullprof-root", type=Path, default=None)
    parser.add_argument("--backend-timeout", type=int, default=120)
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
        "--output-root",
        type=Path,
        help="Override artifact root. Default: <sample-dir>/metadata/dara/batch_*/samples/<sample-slug>",
    )
    parser.add_argument(
        "--batch-id",
        default=None,
        help=(
            "Batch ID for grouping samples (e.g., 'batch_001'). If not provided, "
            "uses the latest batch or creates batch_001."
        ),
    )
    return parser


def parse_backend_list(args: argparse.Namespace) -> list[str]:
    if not args.compare_refinement_backends:
        return [args.refinement_backend]
    backends = [item.strip().lower() for item in args.compare_refinement_backends.split(",") if item.strip()]
    invalid = [item for item in backends if item not in {"bgmn", "gsas", "fullprof"}]
    if invalid:
        raise ValueError(f"Invalid refinement backend(s): {', '.join(invalid)}")
    return list(dict.fromkeys(backends))


def build_backend_options(args: argparse.Namespace) -> dict[str, object]:
    options: dict[str, object] = {"backend_timeout": args.backend_timeout, "timeout": args.backend_timeout}
    if args.gsas_instprm is not None:
        options["gsas_instprm"] = args.gsas_instprm.resolve().as_posix()
    if args.gsas_conda_env:
        options["gsas_conda_env"] = args.gsas_conda_env
    else:
        options["gsas_conda_env"] = None
    if args.fullprof_root is not None:
        options["fullprof_root"] = args.fullprof_root.resolve().as_posix()
    return options


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
        "COMBINED": [
            CODDatabase(dara_root / "cod_cifs"),
            ICSDDatabase(dara_root / "icsd_cifs"),
        ],
    }
    return database_map[database_name]


def extract_document(response, job_uuid):
    return response[job_uuid][1].output


def serialize_grouped_phases(grouped_phases) -> list[dict[str, object]]:
    serialized: list[dict[str, object]] = []
    for result_index, grouped_result in enumerate((grouped_phases or [])[:10], start=1):
        phase_buckets = []
        for phase_bucket_index, phase_bucket in enumerate(grouped_result, start=1):
            clusters = []
            for head_formula, cif_stems in phase_bucket:
                clusters.append(
                    {
                        "head_formula": str(head_formula),
                        "cif_stems": list(cif_stems),
                    }
                )
            phase_buckets.append(
                {
                    "phase_bucket": phase_bucket_index,
                    "clusters": clusters,
                }
            )
        serialized.append({"rank": result_index, "phase_buckets": phase_buckets})
    return serialized


def extract_refinement_summary(refinement_result) -> list[dict[str, object]]:
    if refinement_result is None:
        return []

    weights = refinement_result.get_phase_weights(normalize=True)
    summary = []
    for phase_name, phase_result in refinement_result.lst_data.phases_results.items():
        summary.append(
            {
                "phase": phase_name,
                "weight_fraction": float(weights.get(phase_name, 0.0)),
                "rphase": phase_result.rphase,
                "spacegroup_no": phase_result.spacegroup_no,
                "hermann_mauguin": phase_result.hermann_mauguin,
            }
        )
    summary.sort(key=lambda item: item["weight_fraction"], reverse=True)
    return summary


def extract_candidate_rwps(jobflow_root: Path) -> dict[int, float]:
    rwp_by_rank: dict[int, float] = {}
    job_dirs = sorted(jobflow_root.glob("job_*"))
    if not job_dirs:
        return rwp_by_rank

    latest_job_dir = job_dirs[-1]
    for candidate_dir in latest_job_dir.iterdir():
        if not candidate_dir.is_dir():
            continue
        match = re.match(r"(?P<rank>\d+)_result_rwp_(?P<rwp>\d+(?:\.\d+)?)$", candidate_dir.name)
        if match is None:
            continue
        rwp_by_rank[int(match.group("rank"))] = float(match.group("rwp"))
    return rwp_by_rank


def extract_candidate_refinements(document, jobflow_root: Path) -> list[dict[str, object]]:
    candidate_groups = serialize_grouped_phases(document.grouped_phases)
    candidate_rwps = extract_candidate_rwps(jobflow_root)
    serialized: list[dict[str, object]] = []
    for result_index, result_tuple in enumerate(document.results or [], start=1):
        refinement_result = result_tuple[1] if len(result_tuple) > 1 else None
        serialized.append(
            {
                "rank": result_index,
                "rwp": candidate_rwps.get(result_index),
                "phase_buckets": (
                    candidate_groups[result_index - 1]["phase_buckets"]
                    if result_index <= len(candidate_groups)
                    else []
                ),
                "refinement": extract_refinement_summary(refinement_result),
            }
        )
    return serialized


def save_refinement_plot(refinement_result, output_path: Path) -> None:
    if refinement_result is None:
        return

    figure = refinement_result.visualize(diff_offset=True)
    figure.write_html(output_path.as_posix())


def run_database(args: argparse.Namespace, pattern_path: Path, output_root: Path) -> dict[str, object]:
    from jobflow.managers.local import run_locally

    from dara.cif import Cif
    from dara.jobs import PhaseSearchMaker
    from dara.resources import DaraResourceBudget
    from dara.xrd import load_pattern

    database_name = args.database_name
    backend_name = getattr(args, "current_refinement_backend", args.refinement_backend)
    run_dir = (
        output_root / backend_name / database_name.lower()
        if args.compare_refinement_backends
        else output_root / database_name.lower()
    )
    jobflow_root = run_dir / "jobflow"
    if jobflow_root.exists():
        remove_tree_with_retries(jobflow_root)
    run_dir.mkdir(parents=True, exist_ok=True)

    additional_cifs = [Cif.from_file(path) for path in args.additional_cif_paths]
    pattern = load_pattern(pattern_path)
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
    ).resolve()

    start_time = time.perf_counter()
    job = PhaseSearchMaker(
        name=f"benchmark_{database_name.lower()}",
        phase_predictor=None,
        verbose=False,
        run_final_refinement=False,
        max_num_results=args.max_results,
    ).make(
        pattern,
        precursors=args.precursor,
        cif_dbs=build_databases(database_name, args.dara_root),
        additional_cifs=additional_cifs or None,
        additional_cif_params={"lattice_range": 0.05},
        search_kwargs={
            "wavelength": args.wavelength,
            "instrument_profile": args.instrument_profile,
            "max_phases": args.max_phases,
            "refinement_params": {"n_threads": args.bgmn_threads},
            "resource_budget": asdict(resource_budget),
            "refinement_backend": backend_name,
            "backend_options": build_backend_options(args),
        },
    )
    response = run_locally(
        job,
        create_folders=True,
        raise_immediately=True,
        root_dir=jobflow_root,
    )
    elapsed_seconds = time.perf_counter() - start_time

    document = extract_document(response, job.uuid)
    best_result = document.results[0][1] if document.results else None

    save_refinement_plot(best_result, run_dir / "best_refinement_plot.html")
    for result_index, result_tuple in enumerate(document.results[:3], start=1):
        save_refinement_plot(result_tuple[1], run_dir / f"candidate_{result_index:02d}_plot.html")

    summary = {
        "database": database_name,
        "refinement_backend": backend_name,
        "backend_options": build_backend_options(args),
        "elapsed_seconds": elapsed_seconds,
        "best_rwp": document.best_rwp,
        "num_results": len(document.results or []),
        "top_candidate_groups": serialize_grouped_phases(document.grouped_phases),
        "candidate_refinements": extract_candidate_refinements(document, jobflow_root),
        "best_refinement": extract_refinement_summary(best_result),
        "artifact_root": run_dir.as_posix(),
        "jobflow_root": jobflow_root.as_posix(),
        "additional_cif_paths": [path.as_posix() for path in args.additional_cif_paths],
        "resource_budget": asdict(resource_budget),
    }
    write_json(run_dir / "summary.json", summary)
    return summary


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.threads < 1 or args.bgmn_threads < 1 or args.max_parallel_jobs < 1:
        parser.error("threads, bgmn-threads, and max-parallel-jobs must all be >= 1")

    args.dara_root = args.dara_root.resolve()
    args.precursor = args.precursor or list(DEFAULT_PRECURSORS)
    args.additional_cif_paths = collect_additional_cif_paths(args)
    os.environ["DARA_MAX_PARALLEL_JOBS"] = str(args.max_parallel_jobs)
    configure_threads(args.threads)
    sys.path.insert(0, str(args.dara_root / "src"))

    sample_path = args.sample_path.resolve()
    run_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if args.output_root:
        output_root = args.output_root.resolve()
    else:
        metadata_root = sample_path.parent / "metadata" / "dara"
        batch_id, batch_dir = find_or_create_batch(metadata_root, args.batch_id)
        output_root = build_batch_sample_output_root(batch_dir, sample_path)
    staged_sample = copy_sample(sample_path, output_root)

    run_note = {
        "run_timestamp": run_timestamp,
        "sample_source": sample_path.as_posix(),
        "output_root": output_root.as_posix(),
        "staged_sample": staged_sample.as_posix(),
        "precursors": args.precursor,
        "wavelength": args.wavelength,
        "instrument_profile": args.instrument_profile,
        "threads": args.threads,
        "bgmn_threads": args.bgmn_threads,
        "max_parallel_jobs": args.max_parallel_jobs,
        "refinement_backend": args.refinement_backend,
        "compare_refinement_backends": args.compare_refinement_backends,
        "gsas_instprm": args.gsas_instprm.as_posix() if args.gsas_instprm else None,
        "gsas_conda_env": args.gsas_conda_env,
        "fullprof_root": args.fullprof_root.as_posix() if args.fullprof_root else None,
        "backend_timeout": args.backend_timeout,
        "resource_profile": args.resource_profile,
        "memory_gb": args.memory_gb,
        "peak_match_chunk_size": args.peak_match_chunk_size,
        "peak_match_batch_size": args.peak_match_batch_size,
        "peak_match_max_pending_batches": args.peak_match_max_pending_batches,
        "ray_object_store_memory_gb": args.ray_object_store_memory_gb,
        "databases": args.database,
        "additional_cif_paths": [path.as_posix() for path in args.additional_cif_paths],
        "additional_cif_dirs": [str(path) for path in args.additional_cif_dir],
        "additional_cif_manifests": [str(path) for path in args.additional_cif_manifest],
    }
    write_json(output_root / "run_note.json", run_note)

    summaries = []
    for backend_name in parse_backend_list(args):
        args.current_refinement_backend = backend_name
        for database_name in args.database:
            args.database_name = database_name
            summaries.append(run_database(args, staged_sample, output_root))

    write_json(
        output_root / "benchmark_summary.json",
        {
            "run_timestamp": run_timestamp,
            "sample_source": sample_path.as_posix(),
            "output_root": output_root.as_posix(),
            "sample": staged_sample.as_posix(),
            "precursors": args.precursor,
            "wavelength": args.wavelength,
            "threads": args.threads,
            "refinement_backends": parse_backend_list(args),
            "results": summaries,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
