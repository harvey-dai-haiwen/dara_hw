from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run_capture(command: list[str], cwd: Path) -> tuple[int, str]:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    return completed.returncode, (completed.stdout + completed.stderr).strip()


def check_path(path: Path, should_exist: bool = True) -> dict[str, object]:
    return {
        "path": path.as_posix(),
        "exists": path.exists(),
        "ok": path.exists() if should_exist else True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a local uv-based Dara checkout and optional database mirrors.")
    parser.add_argument("--structure-index", type=Path, default=None)
    parser.add_argument("--run-pytest", action="store_true")
    parser.add_argument("--run-smoke", action="store_true")
    parser.add_argument("--json-output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    uv = shutil.which("uv")
    report: dict[str, object] = {
        "repo_root": repo_root.as_posix(),
        "uv_on_path": uv,
        "checks": {},
    }

    if uv is None:
        report["status"] = "failed"
        report["error"] = "uv is not available on PATH"
        print(json.dumps(report, indent=2))
        return 2

    code, output = run_capture(
        [
            "uv",
            "run",
            "python",
            "-c",
            "import sys, dara; print(sys.executable); print(dara.__file__)",
        ],
        cwd=repo_root,
    )
    report["checks"]["uv_python"] = {"ok": code == 0, "output": output}

    code, output = run_capture(["uv", "run", "dara-search-match", "--help"], cwd=repo_root)
    report["checks"]["dara_search_match_cli"] = {"ok": code == 0, "output_head": output[:1000]}

    code, output = run_capture(["uv", "run", "dara", "server", "--help"], cwd=repo_root)
    report["checks"]["dara_server_cli"] = {"ok": code == 0, "output_head": output[:1000]}

    code, output = run_capture(
        [
            "uv",
            "run",
            "python",
            "-c",
            (
                "from dara.settings import DaraSettings; "
                "s=DaraSettings(); "
                "print(s.PATH_TO_STRUCTURE_INDEX); print(s.PATH_TO_COD); print(s.PATH_TO_ICSD); print(s.PATH_TO_MP)"
            ),
        ],
        cwd=repo_root,
    )
    report["checks"]["dara_settings"] = {"ok": code == 0, "output": output}

    if args.structure_index is not None:
        root = args.structure_index.expanduser()
    else:
        settings_lines = output.splitlines() if code == 0 else []
        root = Path(settings_lines[0]) if settings_lines else Path("~/Structure_index").expanduser()

    report["structure_index"] = {
        "root": check_path(root),
        "cod_cifs": check_path(root / "cod_cifs", should_exist=False),
        "icsd_cifs": check_path(root / "icsd_cifs", should_exist=False),
        "mp_cifs": check_path(root / "mp_cifs", should_exist=False),
        "indexes": check_path(root / "indexes", should_exist=False),
        "mp_json_index": check_path(root / "indexes" / "mp_index.jsonl.gz", should_exist=False),
        "mp_parquet_index": check_path(root / "indexes" / "mp_index.parquet", should_exist=False),
    }

    if args.run_pytest:
        code, output = run_capture(["uv", "run", "pytest", "-q"], cwd=repo_root)
        report["checks"]["pytest"] = {"ok": code == 0, "output_tail": output[-4000:]}

    if args.run_smoke:
        smoke_root = repo_root / ".tmp" / "validate-local-smoke"
        code, output = run_capture(
            [
                "uv",
                "run",
                "dara-search-match",
                "--xrd",
                "tests/test_data/BiFeO3.xy",
                "--output-root",
                smoke_root.as_posix(),
                "--no-database",
                "--additional-cif",
                "tests/test_data/BiFeO3.cif",
                "--must-element",
                "Bi",
                "--must-element",
                "Fe",
                "--possible-element",
                "O",
                "--logical-threads",
                "4",
                "--memory-gb",
                "16",
                "--cpu-target-fraction",
                "0.5",
                "--max-phases",
                "1",
                "--max-results",
                "1",
                "--bgmn-threads",
                "1",
                "--max-parallel-jobs",
                "1",
                "--backend-timeout",
                "180",
            ],
            cwd=repo_root,
        )
        report["checks"]["local_bgmn_smoke"] = {
            "ok": code == 0,
            "output_tail": output[-4000:],
            "expected_plot": (smoke_root / "searchmatch" / "rank_001" / "refinement_plot.html").as_posix(),
        }

    ok = all(
        isinstance(value, dict) and bool(value.get("ok"))
        for value in report["checks"].values()
    )
    report["status"] = "ok" if ok else "failed"
    text = json.dumps(report, indent=2)
    print(text)
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(text, encoding="utf-8")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
