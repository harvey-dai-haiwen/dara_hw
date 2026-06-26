"""Run one fixed real-XRD Dara skill-stability case.

This helper intentionally keeps the task small and deterministic for comparing
agent environments: each case uses a real XRD pattern plus a fixed local CIF
candidate pack, then calls the public Dara CLI with no database lookup.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-json", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--cpu-target-fraction", type=float, default=0.60)
    parser.add_argument("--bgmn-threads", type=int, default=4)
    parser.add_argument("--max-parallel-jobs", type=int, default=4)
    parser.add_argument("--max-phases", type=int, default=3)
    parser.add_argument("--max-results", type=int, default=3)
    parser.add_argument("--instrument-profile", default="Aeris-fds-Pixcel1d-Medipix3")
    args = parser.parse_args()

    case = json.loads(Path(args.case_json).read_text(encoding="utf-8"))
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "dara.search_match_cli",
        "--xrd",
        case["xrd"],
        "--output-root",
        str(output_root),
        "--no-database",
        "--additional-cif-dir",
        case["candidate_dir"],
        "--instrument-profile",
        args.instrument_profile,
        "--wavelength",
        case.get("wavelength", "Cu"),
        "--physical-cores",
        "16",
        "--logical-threads",
        "32",
        "--memory-gb",
        "128",
        "--cpu-target-fraction",
        str(args.cpu_target_fraction),
        "--threads",
        "1",
        "--bgmn-threads",
        str(args.bgmn_threads),
        "--max-parallel-jobs",
        str(args.max_parallel_jobs),
        "--max-phases",
        str(args.max_phases),
        "--max-results",
        str(args.max_results),
    ]

    started = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )
    elapsed = time.perf_counter() - started

    summary_path = output_root / "summary.json"
    case_result: dict[str, object] = {
        "case_id": case["case_id"],
        "label": case["label"],
        "command": cmd,
        "returncode": proc.returncode,
        "elapsed_seconds": elapsed,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
        "summary_path": str(summary_path),
        "summary_exists": summary_path.exists(),
    }
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
        case_result.update(
            {
                "status": summary.get("status"),
                "candidate_count": summary.get("candidate_count"),
                "result_count": summary.get("result_count"),
                "best_rwp": summary.get("best_rwp"),
                "best_phases": summary.get("best_phases"),
                "has_rank1_plot": (output_root / "searchmatch" / "rank_001" / "refinement_plot.html").exists(),
                "has_rank1_fractions": (output_root / "searchmatch" / "rank_001" / "phase_fractions.csv").exists(),
            }
        )
    (output_root / "case_run_result.json").write_text(
        json.dumps(case_result, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(case_result, indent=2))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
