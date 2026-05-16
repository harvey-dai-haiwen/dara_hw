"""Command line interface for Dara search-match workflows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from dara.search_match import (
    DaraSearchMatchConfig,
    ElementFilterConfig,
    ExternalCsvConfig,
    MachineConfig,
    run_search_match,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the search-match argument parser."""
    parser = argparse.ArgumentParser(
        description="Run Dara candidate filtering, search-match, refinement export, and summary generation.",
    )
    parser.add_argument("--dara-root", type=Path, default=Path.cwd())
    parser.add_argument("--xrd", "--sample-path", dest="sample_path", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--database", action="append", choices=["ICSD", "COD", "MP"], default=None)
    parser.add_argument("--no-database", action="store_true", help="Use only additional/external CIFs.")
    parser.add_argument("--precursor", action="append", default=[])

    parser.add_argument("--must-element", action="append", default=[])
    parser.add_argument("--any-element", action="append", default=[])
    parser.add_argument("--any-expression", default=None)
    parser.add_argument("--possible-element", action="append", default=[])

    parser.add_argument("--additional-cif", action="append", default=[])
    parser.add_argument("--additional-cif-dir", action="append", default=[])
    parser.add_argument("--external-csv", action="append", default=[])
    parser.add_argument("--external-csv-cif-column", default=None)
    parser.add_argument("--external-csv-symprec", type=float, default=0.1)
    parser.add_argument("--external-csv-angle-tolerance", type=float, default=5.0)
    parser.add_argument("--external-csv-limit", type=int, default=None)
    parser.add_argument("--disable-structure-dedupe", action="store_true")

    parser.add_argument("--instrument-profile", default="Aeris-fds-Pixcel1d-Medipix3")
    parser.add_argument("--wavelength", default="Cu")
    parser.add_argument("--max-phases", type=int, default=4)
    parser.add_argument("--max-results", type=int, default=1000)
    parser.add_argument("--refinement-backend", choices=["bgmn", "gsas", "fullprof"], default="bgmn")
    parser.add_argument("--backend-timeout", type=int, default=None)
    parser.add_argument("--gsas-instprm", type=Path, default=None)
    parser.add_argument("--fullprof-root", type=Path, default=None)

    parser.add_argument("--resource-profile", choices=["auto", "small", "medium", "large"], default="auto")
    parser.add_argument("--physical-cores", type=int, default=None)
    parser.add_argument("--logical-threads", type=int, default=None)
    parser.add_argument("--memory-gb", type=float, default=None)
    parser.add_argument("--cpu-target-fraction", type=float, default=0.75)
    parser.add_argument("--target-cpus", type=int, default=None)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--bgmn-threads", type=int, default=4)
    parser.add_argument("--max-parallel-jobs", type=int, default=None)
    parser.add_argument("--peak-match-chunk-size", type=int, default=None)
    parser.add_argument("--peak-match-batch-size", type=int, default=None)
    parser.add_argument("--peak-match-max-pending-batches", type=int, default=None)
    parser.add_argument("--ray-object-store-memory-gb", type=float, default=None)
    parser.add_argument("--ray-local-mode", action="store_true")

    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep-work", action="store_true")
    parser.add_argument("--skip-refinement-export", action="store_true")
    return parser


def _backend_options(args: argparse.Namespace) -> dict[str, Any]:
    options: dict[str, Any] = {}
    if args.backend_timeout is not None:
        options["backend_timeout"] = args.backend_timeout
    if args.gsas_instprm is not None:
        options["gsas_instprm"] = args.gsas_instprm.as_posix()
    if args.fullprof_root is not None:
        options["fullprof_root"] = args.fullprof_root.as_posix()
    return options


def config_from_args(args: argparse.Namespace) -> DaraSearchMatchConfig:
    """Convert parsed arguments into the public workflow config."""
    external_csvs = tuple(
        ExternalCsvConfig(
            path=Path(path),
            cif_column=args.external_csv_cif_column,
            symprec=args.external_csv_symprec,
            angle_tolerance=args.external_csv_angle_tolerance,
            limit=args.external_csv_limit,
        )
        for path in args.external_csv
    )
    return DaraSearchMatchConfig(
        dara_root=args.dara_root,
        sample_path=args.sample_path,
        output_root=args.output_root,
        databases=() if args.no_database else tuple(args.database or ["ICSD"]),
        precursors=tuple(args.precursor),
        element_filter=ElementFilterConfig(
            must=tuple(args.must_element),
            any=tuple(args.any_element),
            any_expression=args.any_expression,
            possible=tuple(args.possible_element),
        ),
        additional_cifs=tuple(Path(path) for path in args.additional_cif),
        additional_cif_dirs=tuple(Path(path) for path in args.additional_cif_dir),
        external_csvs=external_csvs,
        disable_structure_dedupe=args.disable_structure_dedupe,
        instrument_profile=args.instrument_profile,
        wavelength=args.wavelength,
        max_phases=args.max_phases,
        max_results=args.max_results,
        refinement_backend=args.refinement_backend,
        backend_options=_backend_options(args),
        machine=MachineConfig(
            physical_cores=args.physical_cores,
            logical_threads=args.logical_threads,
            memory_gb=args.memory_gb,
            cpu_target_fraction=args.cpu_target_fraction,
            target_cpus=args.target_cpus,
            resource_profile=args.resource_profile,
            native_threads=args.threads,
            bgmn_threads=args.bgmn_threads,
            max_parallel_jobs=args.max_parallel_jobs,
            peak_match_chunk_size=args.peak_match_chunk_size,
            peak_match_batch_size=args.peak_match_batch_size,
            peak_match_max_pending_batches=args.peak_match_max_pending_batches,
            ray_object_store_memory_gb=args.ray_object_store_memory_gb,
            ray_local_mode=args.ray_local_mode,
        ),
        dry_run=args.dry_run,
        keep_work=args.keep_work,
        skip_refinement_export=args.skip_refinement_export,
    )


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    args = build_parser().parse_args(argv)
    summary = run_search_match(config_from_args(args))
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("status") in {"ok", "planned"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
