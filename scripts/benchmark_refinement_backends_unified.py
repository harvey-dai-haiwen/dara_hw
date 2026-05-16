"""Compare Dara refinement backends through the unified backend API.

This benchmark is backend-kernel focused: it runs the same pattern/CIF pairs
through ``do_refinement_no_saving(..., backend=...)`` and records wall time,
per-job time, Rwp, and failure rate.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import statistics
import time
import traceback
from pathlib import Path
from typing import Any


DARA_ROOT = Path(__file__).resolve().parents[1]
CASE_DEFAULTS = {
    "YMO": {
        "sample_path": Path(r"D:\XRD_Analysis\DTMA_YMoO3\20231212_YCl3Onepot_1200.xy"),
        "candidates_json": DARA_ROOT / "benchmarks" / "engine_compare" / "ymo_candidates.json",
    },
    "ZnVO": {
        "sample_path": Path(r"D:\XRD_Analysis\VO2+ZnO_Sigma_IMRE_1050_4h.xy"),
        "candidates_json": DARA_ROOT / "benchmarks" / "engine_compare" / "znvo_candidates.json",
    },
}
THREAD_ENV_VARS = (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "NUMEXPR_MAX_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
    "TBB_NUM_THREADS",
    "POLARS_MAX_THREADS",
)
PHASE_PARAMS = {
    "gewicht": "0_0",
    "lattice_range": 0.01,
    "k1": "0_0^0.01",
    "k2": "fixed",
    "b1": "0_0^0.005",
    "rp": 4,
}


def _cap_native_threads(threads: int) -> None:
    for variable in THREAD_ENV_VARS:
        os.environ[variable] = str(max(1, int(threads)))


def _load_candidates(path: Path, limit: int) -> list[Path]:
    data = json.loads(path.read_text(encoding="utf-8"))
    candidates = [Path(item) for item in data["candidate_paths"]]
    return candidates[:limit] if limit > 0 else candidates


def _run_task(task: dict[str, Any]) -> dict[str, Any]:
    _cap_native_threads(int(task["native_threads"]))
    start = time.perf_counter()
    backend = task["backend"]
    try:
        from dara import do_refinement_no_saving
        from dara.refine import RefinementPhase

        backend_options: dict[str, Any] = {
            "backend_timeout": int(task["task_timeout"]),
            "timeout": int(task["task_timeout"]),
        }
        if backend == "gsas":
            backend_options["gsas_conda_env"] = task.get("gsas_conda_env") or "GSASII_fix"
        if backend == "fullprof" and task.get("fullprof_root"):
            backend_options["fullprof_root"] = task["fullprof_root"]

        result = do_refinement_no_saving(
            task["sample_path"],
            [RefinementPhase(path=task["cif_path"])],
            wavelength="Cu",
            instrument_profile="Aeris-fds-Pixcel1d-Medipix3",
            phase_params=PHASE_PARAMS,
            refinement_params={
                "eps1": 0,
                "eps2": "0_-0.05^0.05",
                "n_threads": int(task["threads_per_job"]),
            },
            backend=backend,
            backend_options=backend_options,
        )
        return {
            "backend": backend,
            "case": task["case"],
            "idx": task["idx"],
            "cif": str(task["cif_path"]),
            "seconds": time.perf_counter() - start,
            "status": "ok",
            "rwp": float(result.lst_data.rwp),
            "weights": {key: float(value) for key, value in result.get_phase_weights().items()},
            "error": None,
        }
    except Exception as exc:
        return {
            "backend": backend,
            "case": task["case"],
            "idx": task["idx"],
            "cif": str(task["cif_path"]),
            "seconds": time.perf_counter() - start,
            "status": "failed",
            "rwp": None,
            "weights": {},
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(limit=8),
        }


def _summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [item for item in items if item["status"] == "ok"]
    seconds = [float(item["seconds"]) for item in ok]
    rwps = [float(item["rwp"]) for item in ok if item.get("rwp") is not None]
    return {
        "evaluated": len(items),
        "ok": len(ok),
        "failed": len(items) - len(ok),
        "median_seconds": statistics.median(seconds) if seconds else None,
        "mean_seconds": statistics.mean(seconds) if seconds else None,
        "min_seconds": min(seconds) if seconds else None,
        "max_seconds": max(seconds) if seconds else None,
        "best_rwp": min(rwps) if rwps else None,
        "median_rwp": statistics.median(rwps) if rwps else None,
    }


def _fmt(value: float | int | None) -> str:
    return "NA" if value is None else f"{float(value):.2f}"


def run(args: argparse.Namespace) -> dict[str, Any]:
    _cap_native_threads(args.native_threads)
    os.environ["DARA_MAX_PARALLEL_JOBS"] = str(args.jobs)
    os.environ["DARA_BGMN_THREADS"] = str(args.threads_per_job)
    os.environ["DARA_MAX_BGMN_TASKS"] = str(args.jobs)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    backends = [item.strip() for item in args.backends.split(",") if item.strip()]
    cases = {case: CASE_DEFAULTS[case] for case in args.cases}
    summary: dict[str, Any] = {
        "resource_policy": {
            "logical_cpus": os.cpu_count(),
            "logical_cpu_budget": args.jobs * args.threads_per_job,
            "cpu_budget_fraction": (args.jobs * args.threads_per_job) / (os.cpu_count() or 1),
            "jobs": args.jobs,
            "threads_per_job": args.threads_per_job,
            "native_threads": args.native_threads,
            "candidate_limit_per_case": args.candidate_limit,
        },
        "backends": {},
    }
    for backend in backends:
        tasks = []
        for case, spec in cases.items():
            candidates = _load_candidates(spec["candidates_json"], args.candidate_limit)
            for idx, cif in enumerate(candidates, start=1):
                tasks.append(
                    {
                        "backend": backend,
                        "case": case,
                        "idx": idx,
                        "sample_path": str(spec["sample_path"]),
                        "cif_path": str(cif),
                        "threads_per_job": args.threads_per_job,
                        "native_threads": args.native_threads,
                        "task_timeout": args.task_timeout,
                        "gsas_conda_env": args.gsas_conda_env,
                        "fullprof_root": args.fullprof_root,
                    }
                )

        start = time.perf_counter()
        results: list[dict[str, Any]] = []
        print(f"RUN {backend} tasks={len(tasks)} jobs={args.jobs}", flush=True)
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.jobs) as executor:
            futures = [executor.submit(_run_task, task) for task in tasks]
            for future in concurrent.futures.as_completed(futures):
                item = future.result()
                results.append(item)
                print(
                    json.dumps(
                        {
                            key: item[key]
                            for key in ["backend", "case", "idx", "seconds", "status", "rwp", "error"]
                        }
                    ),
                    flush=True,
                )

        results.sort(key=lambda item: (item["case"], item["idx"]))
        backend_summary = {
            "wall_seconds": time.perf_counter() - start,
            "overall": _summarize(results),
            "cases": {
                case: _summarize([item for item in results if item["case"] == case])
                for case in cases
            },
        }
        summary["backends"][backend] = backend_summary
        (output_dir / f"{backend}_details.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        (output_dir / f"{backend}_summary.json").write_text(
            json.dumps(backend_summary, indent=2),
            encoding="utf-8",
        )

    (output_dir / "combined_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [
        "# Dara refinement backend speed comparison (50% logical CPU)",
        "",
        f"- logical CPUs: {summary['resource_policy']['logical_cpus']}",
        f"- budget: {summary['resource_policy']['logical_cpu_budget']} logical CPUs "
        f"({summary['resource_policy']['cpu_budget_fraction']:.0%})",
        f"- candidates: {args.candidate_limit} per case x {len(cases)} cases = "
        f"{args.candidate_limit * len(cases)} per backend",
        "",
        "| Backend | Wall s | OK/Total | Median s/job | Mean s/job | Best Rwp | Median Rwp |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for backend in backends:
        backend_summary = summary["backends"][backend]
        overall = backend_summary["overall"]
        lines.append(
            f"| {backend} | {backend_summary['wall_seconds']:.2f} | "
            f"{overall['ok']}/{overall['evaluated']} | {_fmt(overall['median_seconds'])} | "
            f"{_fmt(overall['mean_seconds'])} | {_fmt(overall['best_rwp'])} | "
            f"{_fmt(overall['median_rwp'])} |"
        )
    lines.extend(["", "## By case", ""])
    for backend in backends:
        lines.append(f"### {backend}")
        lines.append("| Case | OK/Total | Median s/job | Best Rwp | Median Rwp |")
        lines.append("|---|---:|---:|---:|---:|")
        for case in cases:
            case_summary = summary["backends"][backend]["cases"][case]
            lines.append(
                f"| {case} | {case_summary['ok']}/{case_summary['evaluated']} | "
                f"{_fmt(case_summary['median_seconds'])} | {_fmt(case_summary['best_rwp'])} | "
                f"{_fmt(case_summary['median_rwp'])} |"
            )
        lines.append("")
    (output_dir / "combined_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("DONE", output_dir, flush=True)
    print("\n".join(lines), flush=True)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backends", default="bgmn,gsas,fullprof")
    parser.add_argument("--cases", nargs="+", choices=tuple(CASE_DEFAULTS), default=["YMO", "ZnVO"])
    parser.add_argument("--candidate-limit", type=int, default=8)
    parser.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    parser.add_argument("--threads-per-job", type=int, default=1)
    parser.add_argument("--native-threads", type=int, default=1)
    parser.add_argument("--task-timeout", type=int, default=240)
    parser.add_argument("--gsas-conda-env", default="GSASII_fix")
    parser.add_argument("--fullprof-root", default=None)
    parser.add_argument(
        "--output-dir",
        default=str(DARA_ROOT / "benchmarks" / "refinement_backend_compare_50pct_unified"),
    )
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
