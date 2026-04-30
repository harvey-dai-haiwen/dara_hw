from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
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
    parser.add_argument("--instrument-profile", default="Aeris-fds-Pixcel1d-Medipix3")
    parser.add_argument("--wavelength", default="Cu")
    parser.add_argument("--max-phases", type=int, default=4)
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--threads", type=int, default=4)
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


def save_refinement_plot(refinement_result, output_path: Path) -> None:
    if refinement_result is None:
        return

    figure = refinement_result.visualize(diff_offset=True)
    figure.write_html(output_path.as_posix())


def run_database(args: argparse.Namespace, pattern_path: Path, output_root: Path) -> dict[str, object]:
    from jobflow.managers.local import run_locally

    from dara.cif import Cif
    from dara.jobs import PhaseSearchMaker
    from dara.xrd import load_pattern

    database_name = args.database_name
    run_dir = output_root / database_name.lower()
    jobflow_root = run_dir / "jobflow"
    if jobflow_root.exists():
        shutil.rmtree(jobflow_root)
    run_dir.mkdir(parents=True, exist_ok=True)

    additional_cifs = [Cif.from_file(resolve_path(args.dara_root, raw_path)) for raw_path in args.additional_cif]
    pattern = load_pattern(pattern_path)

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
        "elapsed_seconds": elapsed_seconds,
        "best_rwp": document.best_rwp,
        "num_results": len(document.results or []),
        "top_candidate_groups": serialize_grouped_phases(document.grouped_phases),
        "best_refinement": extract_refinement_summary(best_result),
        "artifact_root": run_dir.as_posix(),
        "jobflow_root": jobflow_root.as_posix(),
    }
    write_json(run_dir / "summary.json", summary)
    return summary


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.dara_root = args.dara_root.resolve()
    args.precursor = args.precursor or list(DEFAULT_PRECURSORS)
    configure_threads(args.threads)
    sys.path.insert(0, str(args.dara_root / "src"))

    sample_path = args.sample_path.resolve()
    sample_slug = slugify(sample_path.stem)
    output_root = args.dara_root / "custom-test-samples" / sample_slug
    staged_sample = copy_sample(sample_path, output_root)

    run_note = {
        "sample_source": sample_path.as_posix(),
        "staged_sample": staged_sample.as_posix(),
        "precursors": args.precursor,
        "wavelength": args.wavelength,
        "instrument_profile": args.instrument_profile,
        "threads": args.threads,
        "databases": args.database,
    }
    write_json(output_root / "run_note.json", run_note)

    summaries = []
    for database_name in args.database:
        args.database_name = database_name
        summaries.append(run_database(args, staged_sample, output_root))

    write_json(
        output_root / "benchmark_summary.json",
        {
            "sample": staged_sample.as_posix(),
            "precursors": args.precursor,
            "wavelength": args.wavelength,
            "threads": args.threads,
            "results": summaries,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())