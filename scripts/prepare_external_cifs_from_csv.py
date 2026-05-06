from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_CSV_NAME = "wf_tnmtps_am20_kgb2.2_Ni-Se-Sn.csv"


def slugify(text: str) -> str:
    lowered = text.lower().strip()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "external-cif"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def resolve_csv_path(series_dir: Path, csv_path: Path | None) -> Path:
    if csv_path is not None:
        return csv_path.resolve()
    return (series_dir / DEFAULT_CSV_NAME).resolve()


def build_next_batch_id(metadata_root: Path, batch_label: str) -> str:
    existing_numbers: list[int] = []
    for child in metadata_root.iterdir():
        if not child.is_dir() or not child.name.startswith("batch_"):
            continue
        match = re.match(r"batch_(\d+)", child.name)
        if match is not None:
            existing_numbers.append(int(match.group(1)))
    next_number = max(existing_numbers, default=0) + 1
    suffix = f"_{slugify(batch_label)}" if batch_label else ""
    return f"batch_{next_number:03d}{suffix}"


def find_or_create_batch(series_dir: Path, batch_id: str | None, batch_label: str) -> tuple[str, Path]:
    metadata_root = series_dir / "metadata" / "dara"
    metadata_root.mkdir(parents=True, exist_ok=True)
    resolved_batch_id = batch_id or build_next_batch_id(metadata_root, batch_label)
    batch_dir = metadata_root / resolved_batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    return resolved_batch_id, batch_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract CIF text from a CSV, symmetrize with pymatgen, and export temporary CIFs for Dara.",
    )
    parser.add_argument("--series-dir", type=Path, required=True)
    parser.add_argument("--csv-path", type=Path, default=None)
    parser.add_argument("--batch-id", default=None)
    parser.add_argument("--batch-label", default="csp_combined_search")
    parser.add_argument("--cif-column", default=None)
    parser.add_argument("--symprec", type=float, default=0.1)
    parser.add_argument("--angle-tolerance", type=float, default=5.0)
    parser.add_argument("--limit", type=int, default=None)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        from dara.external_candidates import prepare_external_cifs_from_csv
    except ImportError as exc:
        parser.error(
            "pymatgen is required for CSV CIF preprocessing. Run this script in Dara's uv environment "
            "or in the Pymatgen_hw conda environment."
        )
        raise exc

    series_dir = args.series_dir.resolve()
    csv_path = resolve_csv_path(series_dir, args.csv_path)
    if not csv_path.exists():
        parser.error(f"CSV file does not exist: {csv_path}")

    batch_id, batch_dir = find_or_create_batch(series_dir, args.batch_id, args.batch_label)
    preprocessing_dir = batch_dir / "preprocessing"
    cif_output_dir = preprocessing_dir / "external-cifs"
    manifest_path = preprocessing_dir / "external_cifs_manifest.json"
    run_note_path = preprocessing_dir / "run_note.json"

    result = prepare_external_cifs_from_csv(
        csv_path,
        cif_output_dir,
        cif_column=args.cif_column,
        symprec=args.symprec,
        angle_tolerance=args.angle_tolerance,
        limit=args.limit,
    )
    manifest = result.manifest
    for item in manifest["generated_cifs"]:
        item["cif_path"] = Path(item["cif_path"]).relative_to(manifest_path.parent).as_posix()

    manifest.update(
        {
            "series_dir": series_dir.as_posix(),
            "batch_id": batch_id,
            "batch_dir": batch_dir.as_posix(),
        }
    )
    write_json(manifest_path, manifest)
    write_json(
        run_note_path,
        {
            "created_at": manifest["created_at"],
            "series_dir": series_dir.as_posix(),
            "csv_path": csv_path.as_posix(),
            "batch_id": batch_id,
            "batch_dir": batch_dir.as_posix(),
            "manifest_path": manifest_path.as_posix(),
            "cif_output_dir": cif_output_dir.as_posix(),
            "cif_column": manifest["cif_column"],
            "python_executable": sys.executable,
            "symprec": args.symprec,
            "angle_tolerance": args.angle_tolerance,
        },
    )

    print(f"batch_id={batch_id}")
    print(f"batch_dir={batch_dir.as_posix()}")
    print(f"manifest_path={manifest_path.as_posix()}")
    print(f"generated_count={manifest['generated_count']}")
    print(f"failure_count={manifest['failure_count']}")
    print(f"skipped_empty_rows={manifest['skipped_empty_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
