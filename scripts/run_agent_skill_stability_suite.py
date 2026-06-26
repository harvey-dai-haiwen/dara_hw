"""Run all fixed real-XRD skill-stability cases sequentially."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--cpu-target-fraction", type=float, default=0.60)
    parser.add_argument("--bgmn-threads", type=int, default=4)
    parser.add_argument("--max-parallel-jobs", type=int, default=4)
    parser.add_argument("--max-phases", type=int, default=3)
    parser.add_argument("--max-results", type=int, default=3)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    results = []
    start = time.perf_counter()
    for case in manifest["cases"]:
        case_output = output_root / case["case_id"]
        cmd = [
            sys.executable,
            "scripts/run_agent_skill_stability_case.py",
            "--case-json",
            case["case_json"],
            "--output-root",
            str(case_output),
            "--cpu-target-fraction",
            str(args.cpu_target_fraction),
            "--bgmn-threads",
            str(args.bgmn_threads),
            "--max-parallel-jobs",
            str(args.max_parallel_jobs),
            "--max-phases",
            str(args.max_phases),
            "--max-results",
            str(args.max_results),
        ]
        case_start = time.perf_counter()
        proc = subprocess.run(
            cmd,
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
        )
        result_path = case_output / "case_run_result.json"
        parsed = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
        parsed.update(
            {
                "case_id": case["case_id"],
                "returncode": proc.returncode,
                "wrapper_elapsed_seconds": time.perf_counter() - case_start,
                "case_stdout_tail": proc.stdout[-3000:],
                "case_stderr_tail": proc.stderr[-3000:],
            }
        )
        results.append(parsed)

    suite = {
        "agent_id": args.agent_id,
        "output_root": str(output_root),
        "elapsed_seconds": time.perf_counter() - start,
        "cpu_target_fraction": args.cpu_target_fraction,
        "bgmn_threads": args.bgmn_threads,
        "max_parallel_jobs": args.max_parallel_jobs,
        "cases": results,
    }
    (output_root / "suite_result.json").write_text(
        json.dumps(suite, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(suite, indent=2))
    failed = [
        item
        for item in results
        if item.get("returncode") != 0
        or item.get("status") != "ok"
        or not item.get("summary_exists")
        or not item.get("has_rank1_plot")
        or not item.get("has_rank1_fractions")
    ]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
