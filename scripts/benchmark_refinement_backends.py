"""Compare BGMN, GSAS-II, and FullProf single-phase refinement throughput.

This is a backend-kernel benchmark, not a full Dara search-tree benchmark.
It refines the same pattern/candidate CIF pairs with the selected backend and
records per-candidate wall time and Rwp-like metrics.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from statistics import mean, median
from typing import Any


DARA_ROOT = Path(__file__).resolve().parents[1]
XRD_SOLVER_ROOT = Path(r"D:\Haiwen\Code_Repositories\XRD structure solution")
GSAS_REPO = XRD_SOLVER_ROOT / "reference repos" / "GSAS-II"
GSAS_INSTPRM = GSAS_REPO / "tests" / "testinp" / "INST_XRY.PRM"
FULLPROF_ROOT = Path(r"D:\Haiwen\Tools\FullProfAPP\runtime\resources\fpsuite\windows")
FULLPROF_EXE = FULLPROF_ROOT / "fp2k.exe"
FULLPROF_CIF_TO_PCR = FULLPROF_ROOT / "CIFs_to_PCR.exe"
FULLPROF_DIM = FULLPROF_ROOT / "fullprof.dim"

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
)


def _cap_native_threads(threads: int) -> None:
    for variable in THREAD_ENV_VARS:
        os.environ[variable] = str(max(1, int(threads)))


def _load_candidates(path: Path, limit: int) -> list[Path]:
    data = json.loads(path.read_text(encoding="utf-8"))
    candidates = [Path(item) for item in data["candidate_paths"]]
    return candidates[:limit] if limit > 0 else candidates


def _sanitize_name(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", path.stem)


def _run_bgmn_task(task: dict[str, Any]) -> dict[str, Any]:
    _cap_native_threads(1)
    start = time.perf_counter()
    try:
        from dara import do_refinement_no_saving
        from dara.refine import RefinementPhase

        result = do_refinement_no_saving(
            task["sample_path"],
            [RefinementPhase(path=task["cif_path"])],
            wavelength="Cu",
            instrument_profile="Aeris-fds-Pixcel1d-Medipix3",
            phase_params={
                "gewicht": "0_0",
                "lattice_range": 0.01,
                "k1": "0_0^0.01",
                "k2": "fixed",
                "b1": "0_0^0.005",
                "rp": 4,
            },
            refinement_params={
                "eps1": 0,
                "eps2": "0_-0.05^0.05",
                "n_threads": int(task["threads_per_job"]),
            },
        )
        rwp = float(result.lst_data.rwp)
        status = "ok"
        error = None
    except Exception as exc:
        rwp = None
        status = "failed"
        error = f"{type(exc).__name__}: {exc}"

    return {
        "backend": "bgmn",
        "case": task["case"],
        "idx": task["idx"],
        "cif": str(task["cif_path"]),
        "seconds": time.perf_counter() - start,
        "status": status,
        "rwp": rwp,
        "error": error,
    }


def _append_if_missing(path: Path) -> None:
    path_str = str(path)
    if path.exists() and path_str in sys.path:
        sys.path.remove(path_str)
    if path.exists():
        sys.path.insert(0, path_str)


def _configure_gsasii() -> None:
    sys.meta_path[:] = [
        finder
        for finder in sys.meta_path
        if "_gsas_ii_editable_loader" not in type(finder).__module__
    ]
    _append_if_missing(GSAS_REPO)
    build_sources = sorted(
        GSAS_REPO.glob("build/*/sources"),
        key=lambda path: path.stat().st_mtime,
    )
    if build_sources:
        _append_if_missing(build_sources[-1])
        import GSASII

        source_str = str(build_sources[-1])
        if source_str not in GSASII.__path__:
            GSASII.__path__.append(source_str)

    import GSASII.GSASIIscriptable as G2sc

    G2sc.LoadG2fil()


def _normalize_cif_for_gsas(source_cif: Path, output_cif: Path) -> Path:
    from pymatgen.core import Structure
    from pymatgen.io.cif import CifWriter

    structure = Structure.from_file(source_cif)
    try:
        structure.remove_oxidation_states()
    except Exception:
        pass
    CifWriter(structure, symprec=0.1).write_file(output_cif)
    return output_cif


def _collect_gsas_metrics(lst_path: Path, residuals: dict[str, Any]) -> dict[str, float | None]:
    metrics: dict[str, float | None] = {
        "Rwp": float(residuals.get("wR")) if residuals.get("wR") is not None else None,
        "Rp": float(residuals.get("R")) if residuals.get("R") is not None else None,
        "Rexp": float(residuals.get("wRmin")) if residuals.get("wRmin") is not None else None,
        "GOF": None,
    }
    if lst_path.exists():
        number = r"([0-9]+(?:\.[0-9]*)?(?:e[+-]?\d+)?)"
        match = re.search(
            rf"wR\s*=\s*{number}%,\s*chi\*\*2\s*=\s*{number},\s*GOF\s*=\s*{number}",
            lst_path.read_text(encoding="utf-8", errors="ignore"),
            flags=re.IGNORECASE,
        )
        if match:
            metrics["Rwp"] = float(match.group(1))
            metrics["GOF"] = float(match.group(3))
    if metrics.get("GOF") is None and metrics.get("Rwp") and metrics.get("Rexp"):
        metrics["GOF"] = float(metrics["Rwp"]) / float(metrics["Rexp"])
    return metrics


def _run_gsas_task(task: dict[str, Any]) -> dict[str, Any]:
    _cap_native_threads(1)
    start = time.perf_counter()
    run_dir = Path(task["run_root"]) / task["case"] / f"{task['idx']:03d}_{_sanitize_name(Path(task['cif_path']))}"
    try:
        _configure_gsasii()
        import GSASII.GSASIIscriptable as G2sc

        run_dir.mkdir(parents=True, exist_ok=True)
        project_path = run_dir / "refinement.gpx"
        lst_path = run_dir / "refinement.lst"
        gsas_cif = _normalize_cif_for_gsas(Path(task["cif_path"]), run_dir / "candidate_phase.cif")

        gpx = G2sc.G2Project(newgpx=str(project_path))
        histogram = gpx.add_powder_histogram(
            str(task["sample_path"]),
            str(GSAS_INSTPRM),
            fmthint="Topas xye",
        )
        phase = gpx.add_phase(
            str(gsas_cif),
            phasename=Path(task["cif_path"]).stem,
            histograms=[histogram],
        )

        histogram.set_refinements({"Limits": [10.0, 90.0]})
        gpx.set_Controls("cycles", 0)
        gpx.refine(makeBack=True)
        gpx.set_Controls("cycles", int(task["cycles"]))
        histogram.set_refinements({"Background": {"no. coeffs": int(task["background_coeffs"]), "refine": True}})
        gpx.refine(makeBack=True)
        phase.set_HAP_refinements({"Scale": True}, [histogram])
        phase.set_refinements({"Cell": True})
        histogram.set_refinements({"Sample Parameters": {"Shift": True}})
        gpx.refine(makeBack=True)

        metrics = _collect_gsas_metrics(lst_path, dict(histogram.residuals))
        rwp = metrics.get("Rwp")
        status = "ok"
        error = None
    except Exception as exc:
        rwp = None
        status = "failed"
        error = f"{type(exc).__name__}: {exc}"

    return {
        "backend": "gsas",
        "case": task["case"],
        "idx": task["idx"],
        "cif": str(task["cif_path"]),
        "seconds": time.perf_counter() - start,
        "status": status,
        "rwp": rwp,
        "error": error,
        "run_dir": str(run_dir),
    }


def _run_text_command(
    command: list[str],
    run_dir: Path,
    stdin: str = "",
    timeout_s: int = 120,
) -> tuple[int, str]:
    import subprocess

    env = os.environ.copy()
    env["PATH"] = str(FULLPROF_ROOT) + os.pathsep + env.get("PATH", "")
    completed = subprocess.run(
        command,
        input=stdin,
        cwd=run_dir,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout_s,
        check=False,
    )
    return completed.returncode, (completed.stdout or "") + (completed.stderr or "")


def _patch_fullprof_pcr(pcr_path: Path, cycles: int, background_coeffs: int) -> None:
    lines = pcr_path.read_text(encoding="latin-1").splitlines()
    background_coeffs = max(0, min(int(background_coeffs), 6))
    for idx, line in enumerate(lines):
        if line.startswith("!NCY  Eps") and idx + 1 < len(lines):
            parts = lines[idx + 1].split()
            if len(parts) >= 10:
                parts[0] = str(max(1, int(cycles)))
                parts[6] = "10.0000"
                parts[8] = "90.0000"
                lines[idx + 1] = (
                    f"{int(parts[0]):3d} {float(parts[1]):5.2f} {float(parts[2]):5.2f} "
                    f"{float(parts[3]):5.2f} {float(parts[4]):5.2f} {float(parts[5]):5.2f} "
                    f"{float(parts[6]):11.4f} {float(parts[7]):10.6f} {float(parts[8]):10.4f} "
                    f"{float(parts[9]):7.3f} {float(parts[10]) if len(parts) > 10 else 0.0:7.3f}"
                )
        elif re.match(r"^\s*0\.00000\s+0\.0\s+0\.00000\s+0\.0\s+0\.00000\s+0\.0\s+0\.000000", line):
            lines[idx] = "  0.00000    1.0  0.00000    0.0  0.00000    0.0 0.000000    0.00   0"
        elif re.match(r"^\s*100\.000\s+0\.000\s+0\.000\s+0\.000\s+0\.000\s+0\.000", line):
            codes = ["0.00"] * 6
            for code_idx in range(background_coeffs):
                codes[code_idx] = f"{code_idx + 2:.2f}"
            if idx + 1 < len(lines):
                lines[idx + 1] = " " + " ".join(f"{code:>11}" for code in codes)
        elif re.match(r"^\s*0\.1000000E-03", line) and idx + 1 < len(lines):
            lines[idx + 1] = "       8.00000     0.000     0.000     0.000     0.000     0.000"
        elif re.match(r"^\s*[-+0-9.]+\s+[-+0-9.]+\s+[-+0-9.]+\s+[-+0-9.]+\s+[-+0-9.]+\s+[-+0-9.]+\s*$", line):
            if idx > 0 and "# Cell Info" in lines[idx - 1] and idx + 1 < len(lines):
                lines[idx + 1] = "    9.00000    9.00000   10.00000    0.00000    0.00000    0.00000"
    pcr_path.write_text("\n".join(lines) + "\n", encoding="ascii")


def _collect_fullprof_metrics(out_path: Path, sum_path: Path) -> dict[str, float | None]:
    text = ""
    for path in (out_path, sum_path):
        if path.exists():
            text += "\n" + path.read_text(encoding="latin-1", errors="ignore")
    metrics: dict[str, float | None] = {"Rwp": None, "Rp": None, "Rexp": None, "GOF": None}
    number = r"([0-9]+(?:\.[0-9]*)?(?:E[+-]?\d+)?)"
    matches = re.findall(
        rf"Conventional Rietveld Rp,Rwp,Re and Chi2:\s*{number}\s+{number}\s+{number}\s+{number}",
        text,
        flags=re.IGNORECASE,
    )
    if matches:
        rp, rwp, rexp, chi2 = matches[-1]
        metrics["Rp"] = float(rp)
        metrics["Rwp"] = float(rwp)
        metrics["Rexp"] = float(rexp)
        metrics["GOF"] = float(chi2)
        return metrics
    matches = re.findall(
        rf"Rp:\s*{number}\s+Rwp:\s*{number}\s+Rexp:\s*{number}\s+Chi2:\s*{number}",
        text,
        flags=re.IGNORECASE,
    )
    if matches:
        rp, rwp, rexp, chi2 = matches[-1]
        metrics["Rp"] = float(rp)
        metrics["Rwp"] = float(rwp)
        metrics["Rexp"] = float(rexp)
        metrics["GOF"] = float(chi2)
    return metrics


def _run_fullprof_task(task: dict[str, Any]) -> dict[str, Any]:
    _cap_native_threads(1)
    start = time.perf_counter()
    run_dir = Path(task["run_root"]) / task["case"] / f"{task['idx']:03d}_{_sanitize_name(Path(task['cif_path']))}"
    fp_exe = Path(task["fp_exe"])
    cif_to_pcr = Path(task["fp_cif_to_pcr"])
    try:
        if not fp_exe.exists():
            raise FileNotFoundError(f"FullProf executable not found: {fp_exe}")
        if not cif_to_pcr.exists():
            raise FileNotFoundError(f"CIFs_to_PCR executable not found: {cif_to_pcr}")
        run_dir.mkdir(parents=True, exist_ok=True)
        stem = "candidate"
        shutil.copy2(task["cif_path"], run_dir / f"{stem}.cif")
        shutil.copy2(task["sample_path"], run_dir / f"{stem}.dat")
        if FULLPROF_DIM.exists():
            shutil.copy2(FULLPROF_DIM, run_dir / FULLPROF_DIM.name)

        convert_code, convert_output = _run_text_command(
            [str(cif_to_pcr), f"{stem}.cif"],
            run_dir,
            stdin="\n",
            timeout_s=int(task["timeout_s"]),
        )
        pcr_path = run_dir / f"{stem}.pcr"
        if not pcr_path.exists():
            raise RuntimeError(f"CIFs_to_PCR failed with code {convert_code}: {convert_output[:1000]}")

        _patch_fullprof_pcr(
            pcr_path,
            cycles=int(task["fp_cycles"]),
            background_coeffs=int(task["background_coeffs"]),
        )
        run_code, run_output = _run_text_command(
            [str(fp_exe)],
            run_dir,
            stdin=f"{stem}\n\n\n",
            timeout_s=int(task["timeout_s"]),
        )
        metrics = _collect_fullprof_metrics(run_dir / f"{stem}.out", run_dir / f"{stem}.sum")
        rwp = metrics.get("Rwp")
        if run_code != 0 and rwp is None:
            raise RuntimeError(f"fp2k failed with code {run_code}: {run_output[:1000]}")
        status = "ok" if rwp is not None else "failed"
        error = None if rwp is not None else "FullProf finished but no Rwp was parsed"
    except Exception as exc:
        rwp = None
        metrics = {}
        status = "failed"
        error = f"{type(exc).__name__}: {exc}"

    return {
        "backend": "fullprof",
        "case": task["case"],
        "idx": task["idx"],
        "cif": str(task["cif_path"]),
        "seconds": time.perf_counter() - start,
        "status": status,
        "rwp": rwp,
        "metrics": metrics,
        "error": error,
        "run_dir": str(run_dir),
    }


def _summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [item for item in results if item["status"] == "ok"]
    seconds = [float(item["seconds"]) for item in ok]
    rwps = [float(item["rwp"]) for item in ok if item.get("rwp") is not None]
    return {
        "evaluated": len(results),
        "ok": len(ok),
        "failed": len(results) - len(ok),
        "seconds_sum_successful_tasks": sum(seconds) if seconds else None,
        "seconds_mean": mean(seconds) if seconds else None,
        "seconds_median": median(seconds) if seconds else None,
        "seconds_min": min(seconds) if seconds else None,
        "seconds_max": max(seconds) if seconds else None,
        "rwp_best": min(rwps) if rwps else None,
        "rwp_median": median(rwps) if rwps else None,
    }


def run_backend(args: argparse.Namespace) -> dict[str, Any]:
    _cap_native_threads(args.native_threads)
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    run_root = output_dir / f"{args.backend}_runs"
    if args.clean and run_root.exists():
        shutil.rmtree(run_root)
    run_root.mkdir(parents=True, exist_ok=True)

    all_results: list[dict[str, Any]] = []
    case_summaries: dict[str, Any] = {}
    start_total = time.perf_counter()
    for case in args.cases:
        spec = CASE_DEFAULTS[case]
        candidates = _load_candidates(spec["candidates_json"], args.candidate_limit)
        tasks = [
            {
                "backend": args.backend,
                "case": case,
                "idx": idx,
                "sample_path": str(spec["sample_path"]),
                "cif_path": str(cif),
                "threads_per_job": args.threads_per_job,
                "cycles": args.gsas_cycles,
                "fp_cycles": args.fp_cycles,
                "background_coeffs": args.background_coeffs,
                "timeout_s": args.task_timeout,
                "fp_exe": args.fp_exe,
                "fp_cif_to_pcr": args.fp_cif_to_pcr,
                "run_root": str(run_root),
            }
            for idx, cif in enumerate(candidates, start=1)
        ]
        worker = {
            "bgmn": _run_bgmn_task,
            "gsas": _run_gsas_task,
            "fullprof": _run_fullprof_task,
        }[args.backend]
        results: list[dict[str, Any]] = []
        with ProcessPoolExecutor(max_workers=args.jobs) as executor:
            futures = [executor.submit(worker, task) for task in tasks]
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                print(json.dumps(result), flush=True)
        results.sort(key=lambda item: item["idx"])
        all_results.extend(results)
        case_summaries[case] = {
            "sample_path": str(spec["sample_path"]),
            "candidate_count": len(candidates),
            **_summarize(results),
        }
        (output_dir / f"{args.backend}_{case}_details.json").write_text(
            json.dumps(results, indent=2),
            encoding="utf-8",
        )

    summary = {
        "backend": args.backend,
        "resource_policy": {
            "logical_cpu_budget": args.jobs * args.threads_per_job,
            "jobs": args.jobs,
            "threads_per_job": args.threads_per_job,
            "native_threads": args.native_threads,
            "gsas_cycles": args.gsas_cycles,
            "fp_cycles": args.fp_cycles,
            "background_coeffs": args.background_coeffs,
        },
        "cases": case_summaries,
        "wall_seconds": time.perf_counter() - start_total,
    }
    (output_dir / f"{args.backend}_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("bgmn", "gsas", "fullprof"), required=True)
    parser.add_argument("--cases", nargs="+", choices=tuple(CASE_DEFAULTS), default=["YMO", "ZnVO"])
    parser.add_argument("--candidate-limit", type=int, default=16)
    parser.add_argument("--jobs", type=int, default=16)
    parser.add_argument("--threads-per-job", type=int, default=1)
    parser.add_argument("--native-threads", type=int, default=1)
    parser.add_argument("--gsas-cycles", type=int, default=2)
    parser.add_argument("--fp-cycles", type=int, default=2)
    parser.add_argument("--background-coeffs", type=int, default=6)
    parser.add_argument("--task-timeout", type=int, default=120)
    parser.add_argument("--fp-exe", default=str(FULLPROF_EXE))
    parser.add_argument("--fp-cif-to-pcr", default=str(FULLPROF_CIF_TO_PCR))
    parser.add_argument("--output-dir", default=str(DARA_ROOT / "benchmarks" / "refinement_backend_compare_50pct"))
    parser.add_argument("--clean", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_backend(args)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
