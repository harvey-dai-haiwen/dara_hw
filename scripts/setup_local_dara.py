from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

COD_ARCHIVE_URL = "http://www.crystallography.net/archives/cod-cifs-mysql.txz"
MPINICSD_PICKLE_NAME = "df_MPinICSD_20250211_withstructure.pkl"


def default_structure_index() -> Path:
    if os.name == "nt":
        return Path(r"D:\Haiwen\Databases\Structure_index")
    return Path("~/Structure_index").expanduser()


def run_command(command: list[str], cwd: Path | None = None) -> None:
    print("+ " + " ".join(command))
    completed = subprocess.run(command, cwd=cwd, text=True, check=False)
    if completed.returncode:
        raise SystemExit(completed.returncode)


def prompt_yes_no(question: str, default: bool = False) -> bool:
    if not sys.stdin.isatty():
        return default
    suffix = "Y/n" if default else "y/N"
    answer = input(f"{question} [{suffix}] ").strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes"}


def ensure_layout(root: Path) -> None:
    for relative in (
        "cod_cifs",
        "cod_cifs/cif",
        "icsd_cifs",
        "icsd_cifs/cif",
        "mp_cifs",
        "indexes",
        "downloads",
    ):
        folder = root / relative
        folder.mkdir(parents=True, exist_ok=True)
        gitkeep = folder / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")


def write_dara_config(config_path: Path, structure_index: Path) -> None:
    config_path = config_path.expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(
        [
            f"PATH_TO_STRUCTURE_INDEX: {structure_index.as_posix()}",
            f"PATH_TO_COD: {(structure_index / 'cod_cifs').as_posix()}",
            f"PATH_TO_ICSD: {(structure_index / 'icsd_cifs').as_posix()}",
            f"PATH_TO_MP: {(structure_index / 'mp_cifs').as_posix()}",
            "",
        ]
    )
    config_path.write_text(text, encoding="utf-8")
    print(f"Wrote Dara config: {config_path}")


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url}")
    with urllib.request.urlopen(url) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    print(f"Downloaded: {destination}")


def extract_txz(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    print(f"Extracting {archive} -> {destination}")
    with tarfile.open(archive, mode="r:xz") as tar:
        tar.extractall(destination)


def setup_cod(args: argparse.Namespace, structure_index: Path) -> None:
    cod_dir = structure_index / "cod_cifs"
    has_cifs = any(cod_dir.rglob("*.cif"))
    if has_cifs:
        print(f"COD CIF mirror already contains CIF files: {cod_dir}")
        return

    archive = args.cod_archive
    if archive is None:
        local_archive = Path(r"D:\Haiwen\Databases\cod-cifs-mysql.txz")
        if local_archive.exists():
            archive = local_archive

    should_download = args.download_cod
    if not should_download and archive is None and not args.non_interactive:
        should_download = prompt_yes_no(
            "No COD CIF mirror was found. Download COD archive from crystallography.net?",
            default=False,
        )

    if should_download:
        archive = structure_index / "downloads" / "cod-cifs-mysql.txz"
        download_file(COD_ARCHIVE_URL, archive)

    if archive is not None:
        if not archive.exists():
            raise FileNotFoundError(f"COD archive not found: {archive}")
        extract_txz(archive, cod_dir)
    else:
        print("COD mirror not configured. You can add it later under cod_cifs/.")


def safe_getattr(obj: Any, name: str) -> Any:
    try:
        return getattr(obj, name)
    except Exception:
        return None


def structure_payload_from_row(row: Any) -> dict[str, Any] | None:
    structure = None
    for name in ("structure", "Structure", "pymatgen_structure"):
        if name in row and row[name] is not None:
            structure = row[name]
            break
    if structure is None:
        return None

    composition = safe_getattr(structure, "composition")
    if composition is None:
        return None

    try:
        formula = composition.reduced_formula
        elements = [str(element) for element in composition.elements]
        sg_info = structure.get_space_group_info()
        spacegroup = sg_info[1]
    except Exception:
        return None

    return {
        "formula": formula,
        "elements": elements,
        "spacegroup": spacegroup,
    }


def first_present(row: Any, names: tuple[str, ...]) -> Any:
    for name in names:
        if name in row:
            value = row[name]
            if value is not None:
                return value
    return None


def build_mp_index_from_pickle(pickle_path: Path, output_path: Path, limit: int | None = None) -> int:
    import pandas as pd

    print(f"Loading MP pickle: {pickle_path}")
    df = pd.read_pickle(pickle_path)
    if limit is not None:
        df = df.head(limit)

    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        row_data = row.to_dict()
        raw_db_id = first_present(row_data, ("raw_db_id", "material_id", "mp_id", "task_id", "db_id"))
        if raw_db_id is None:
            continue
        raw_db_id = str(raw_db_id)
        if not raw_db_id.startswith(("mp-", "mvc-", "mvl-")) and raw_db_id.isdigit():
            raw_db_id = f"mp-{raw_db_id}"

        payload = structure_payload_from_row(row_data) or {}
        formula = first_present(row_data, ("formula", "pretty_formula", "reduced_formula")) or payload.get("formula")
        elements = first_present(row_data, ("elements", "chemsys_elements")) or payload.get("elements")
        spacegroup = first_present(row_data, ("spacegroup", "spacegroup_number", "sg", "sg_number")) or payload.get(
            "spacegroup"
        )
        energy_above_hull = first_present(row_data, ("energy_above_hull", "e_above_hull", "e_hull"))

        if formula is None or elements is None:
            continue
        if isinstance(elements, str):
            elements = [item for item in elements.replace("-", " ").replace(",", " ").split() if item]
        if not isinstance(elements, (list, tuple, set)):
            continue

        rows.append(
            {
                "raw_db_id": raw_db_id,
                "formula": str(formula),
                "elements": [str(element) for element in elements],
                "spacegroup": int(spacegroup) if str(spacegroup).isdigit() else spacegroup,
                "energy_above_hull": float(energy_above_hull) if energy_above_hull is not None else None,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output_path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    print(f"Wrote MP JSON index: {output_path} ({len(rows)} rows)")

    parquet_path = output_path.with_suffix("").with_suffix(".parquet")
    try:
        pd.DataFrame(rows).to_parquet(parquet_path, index=False)
        print(f"Wrote MP parquet index: {parquet_path}")
    except Exception as exc:
        print(f"Parquet export skipped: {exc}")

    return len(rows)


def setup_mp(args: argparse.Namespace, structure_index: Path) -> None:
    source = args.mp_pickle
    if source is None:
        default_source = Path(r"D:\Haiwen\Databases") / MPINICSD_PICKLE_NAME
        if default_source.exists():
            source = default_source

    if source is None:
        print("MP pickle not configured. You can add MP CIFs under mp_cifs/ and build an index later.")
        return

    if not source.exists():
        raise FileNotFoundError(f"MP pickle not found: {source}")

    target = structure_index / "indexes" / MPINICSD_PICKLE_NAME
    if args.copy_mp_pickle and source.resolve() != target.resolve():
        target.parent.mkdir(parents=True, exist_ok=True)
        print(f"Copying MP pickle for CIF_index Git LFS: {source} -> {target}")
        shutil.copy2(source, target)

    if args.build_mp_index:
        build_mp_index_from_pickle(
            source,
            structure_index / "indexes" / "mp_index.jsonl.gz",
            limit=args.mp_index_limit,
        )


def write_manifest(structure_index: Path) -> None:
    cif_roots = []
    for name in ("cod_cifs", "icsd_cifs", "mp_cifs"):
        path = structure_index / name
        cif_roots.append(
            {
                "name": name,
                "path": path.as_posix(),
                "cif_count": sum(1 for _ in path.rglob("*.cif")) if path.exists() else 0,
                "tracked_in_git": False,
            }
        )

    indexes = []
    for path in sorted((structure_index / "indexes").glob("*")):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        indexes.append(
            {
                "name": path.name,
                "bytes": path.stat().st_size,
                "git_lfs": path.suffix.lower() in {".sqlite", ".pkl"},
            }
        )

    manifest = {
        "repository": "CIF_index",
        "structure_index_root": structure_index.as_posix(),
        "generated_at": datetime.now().replace(microsecond=0).isoformat(),
        "cif_roots": cif_roots,
        "indexes": indexes,
        "dara_config": "dara.yaml.example",
        "raw_cif_policy": "Raw COD/ICSD/MP CIF mirrors stay local and are not committed.",
    }
    path = structure_index / "database_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote database manifest: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Set up a local uv-based Dara checkout and Structure_index database root.")
    parser.add_argument("--structure-index", type=Path, default=default_structure_index())
    parser.add_argument("--config-file", type=Path, default=Path("~/.dara.yaml"))
    parser.add_argument("--skip-uv-sync", action="store_true")
    parser.add_argument("--download-cod", action="store_true")
    parser.add_argument("--cod-archive", type=Path, default=None)
    parser.add_argument("--mp-pickle", type=Path, default=None)
    parser.add_argument("--copy-mp-pickle", action="store_true")
    parser.add_argument("--build-mp-index", action="store_true")
    parser.add_argument("--mp-index-limit", type=int, default=None)
    parser.add_argument("--non-interactive", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    structure_index = args.structure_index.expanduser().resolve()

    if not args.skip_uv_sync:
        run_command(["uv", "sync", "--extra", "tests"], cwd=repo_root)

    ensure_layout(structure_index)
    write_dara_config(args.config_file, structure_index)
    setup_cod(args, structure_index)
    setup_mp(args, structure_index)
    write_manifest(structure_index)

    print("Local Dara setup complete.")
    print("Validate with: uv run python scripts/validate_local_setup.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
