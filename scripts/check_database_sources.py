from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from setup_local_dara import CIF_INDEX_REPO_URL, COD_ARCHIVE_URL, MPINICSD_PICKLE_NAME, default_structure_index


def run_capture(command: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def check_cod_head(url: str, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            headers = dict(response.headers.items())
            return {
                "ok": 200 <= response.status < 400,
                "status": response.status,
                "content_length": int(headers.get("Content-Length", "0") or 0),
                "accept_ranges": headers.get("Accept-Ranges"),
                "last_modified": headers.get("Last-Modified"),
            }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def inspect_lfs_pointer(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "path": path.as_posix(), "error": "missing"}
    head = path.read_text(encoding="utf-8", errors="replace").splitlines()[:4]
    oid = next((line.removeprefix("oid sha256:") for line in head if line.startswith("oid sha256:")), None)
    size_text = next((line.removeprefix("size ") for line in head if line.startswith("size ")), None)
    return {
        "ok": bool(oid and size_text),
        "path": path.as_posix(),
        "is_lfs_pointer": bool(oid and size_text),
        "oid": oid,
        "size": int(size_text) if size_text and size_text.isdigit() else None,
        "head": head,
    }


def clone_cif_index_skip_lfs(repo_url: str, timeout: int) -> dict[str, Any]:
    temp_dir = Path(tempfile.mkdtemp(prefix="dara_cif_index_check_"))
    checkout = temp_dir / "Structure_index"
    env = os.environ.copy()
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    try:
        clone = run_capture(["git", "clone", "--depth", "1", repo_url, str(checkout)], env=env)
        if not clone["ok"]:
            return {"ok": False, "temp_dir": temp_dir.as_posix(), "clone": clone}

        lfs_files = run_capture(["git", "lfs", "ls-files", "-l"], cwd=checkout)
        pointer = inspect_lfs_pointer(checkout / "indexes" / MPINICSD_PICKLE_NAME)
        return {
            "ok": clone["ok"] and lfs_files["ok"] and pointer["ok"],
            "temp_dir": temp_dir.as_posix(),
            "clone": clone,
            "lfs_files": lfs_files,
            "mp_pickle_pointer": pointer,
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def inspect_local_structure_index(root: Path) -> dict[str, Any]:
    indexes = root / "indexes"
    mp_pickle = indexes / MPINICSD_PICKLE_NAME
    report: dict[str, Any] = {
        "root": root.as_posix(),
        "exists": root.exists(),
        "is_git_checkout": (root / ".git").exists(),
        "indexes_exists": indexes.exists(),
        "mp_pickle_exists": mp_pickle.exists(),
    }
    if mp_pickle.exists():
        with mp_pickle.open("rb") as handle:
            first_bytes = handle.read(64)
        report["mp_pickle_is_lfs_pointer"] = first_bytes.startswith(b"version https://git-lfs.github.com/spec")
        report["mp_pickle_bytes"] = mp_pickle.stat().st_size
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Dara database source links without downloading full databases.")
    parser.add_argument("--structure-index", type=Path, default=default_structure_index())
    parser.add_argument("--cif-index-repo", default=CIF_INDEX_REPO_URL)
    parser.add_argument("--cod-url", default=COD_ARCHIVE_URL)
    parser.add_argument("--skip-clone-test", action="store_true")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--json-output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report: dict[str, Any] = {
        "cif_index_repo": args.cif_index_repo,
        "cod_url": args.cod_url,
        "checks": {},
    }
    report["checks"]["git_lfs_version"] = run_capture(["git", "lfs", "version"])
    report["checks"]["cif_index_ls_remote"] = run_capture(["git", "ls-remote", args.cif_index_repo, "refs/heads/main"])
    report["checks"]["cod_archive_head"] = check_cod_head(args.cod_url, timeout=args.timeout)
    report["checks"]["local_structure_index"] = inspect_local_structure_index(args.structure_index.expanduser())

    if not args.skip_clone_test:
        report["checks"]["cif_index_skip_lfs_clone"] = clone_cif_index_skip_lfs(args.cif_index_repo, timeout=args.timeout)

    ok = all(check.get("ok", True) for check in report["checks"].values() if isinstance(check, dict))
    report["status"] = "ok" if ok else "failed"
    text = json.dumps(report, indent=2)
    print(text)
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(text + "\n", encoding="utf-8")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
