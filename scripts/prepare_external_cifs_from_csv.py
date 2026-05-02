from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_CSV_NAME = "wf_tnmtps_am20_kgb2.2_Ni-Se-Sn.csv"


def slugify(text: str) -> str:
    lowered = text.lower().strip()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "external-cif"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def configure_csv_field_size_limit() -> None:
    limit = sys.maxsize
    while limit > 0:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


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


def detect_cif_column(fieldnames: list[str], override: str | None) -> str:
    if override:
        if override not in fieldnames:
            raise ValueError(f"Requested CIF column '{override}' not found in CSV header")
        return override

    cif_candidates = [name for name in fieldnames if "cif" in name.lower()]
    if not cif_candidates:
        raise ValueError("Could not detect a CIF column in the CSV header")

    preferred = sorted(
        cif_candidates,
        key=lambda name: (
            "optimized" not in name.lower(),
            "cif" not in name.lower(),
            len(name),
        ),
    )
    return preferred[0]


def sanitize_structure(structure, symprec: float, angle_tolerance: float):
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    analyzer = SpacegroupAnalyzer(structure, symprec=symprec, angle_tolerance=angle_tolerance)
    refined = analyzer.get_refined_structure()
    return refined, analyzer.get_space_group_symbol(), analyzer.get_space_group_number()


def export_structure(structure, output_path: Path) -> None:
    from pymatgen.io.cif import CifWriter

    output_path.parent.mkdir(parents=True, exist_ok=True)
    CifWriter(structure).write_file(output_path)


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
        from pymatgen.core import Structure
    except ImportError as exc:
        parser.error(
            "pymatgen is required for CSV CIF preprocessing. Run this script in Dara's uv environment or in the Pymatgen_hw conda environment."
        )
        raise exc

    configure_csv_field_size_limit()

    series_dir = args.series_dir.resolve()
    csv_path = resolve_csv_path(series_dir, args.csv_path)
    if not csv_path.exists():
        parser.error(f"CSV file does not exist: {csv_path}")

    batch_id, batch_dir = find_or_create_batch(series_dir, args.batch_id, args.batch_label)
    preprocessing_dir = batch_dir / "preprocessing"
    cif_output_dir = preprocessing_dir / "external-cifs"
    manifest_path = preprocessing_dir / "external_cifs_manifest.json"
    run_note_path = preprocessing_dir / "run_note.json"

    generated_cifs: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    skipped_rows = 0

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            parser.error("CSV header is missing")
        cif_column = detect_cif_column(reader.fieldnames, args.cif_column)

        for row_index, row in enumerate(reader, start=2):
            cif_text = (row.get(cif_column) or "").strip()
            if not cif_text:
                skipped_rows += 1
                continue

            immutable_id = (row.get("immutable_id") or f"row_{row_index}").strip()
            chemsys = (row.get("chemsys") or "").strip()
            stem = slugify(immutable_id)

            try:
                structure = Structure.from_str(cif_text, fmt="cif")
            except Exception as exc:
                failures.append(
                    {
                        "row_index": row_index,
                        "immutable_id": immutable_id,
                        "chemsys": chemsys,
                        "status": "parse_failed",
                        "error": str(exc),
                    }
                )
                continue

            exported_structure = structure
            symmetrized = False
            symmetry_symbol = None
            symmetry_number = None
            symmetry_error = None
            try:
                exported_structure, symmetry_symbol, symmetry_number = sanitize_structure(
                    structure,
                    symprec=args.symprec,
                    angle_tolerance=args.angle_tolerance,
                )
                symmetrized = True
            except Exception as exc:
                symmetry_error = str(exc)

            output_path = cif_output_dir / f"{stem}.cif"
            export_structure(exported_structure, output_path)
            generated_cifs.append(
                {
                    "row_index": row_index,
                    "immutable_id": immutable_id,
                    "chemsys": chemsys,
                    "status": "symmetrized" if symmetrized else "fallback_original_structure",
                    "symmetry_symbol": symmetry_symbol,
                    "symmetry_number": symmetry_number,
                    "symmetry_error": symmetry_error,
                    "cif_path": output_path.relative_to(manifest_path.parent).as_posix(),
                }
            )

            if args.limit is not None and len(generated_cifs) >= args.limit:
                break

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "series_dir": series_dir.as_posix(),
        "csv_path": csv_path.as_posix(),
        "batch_id": batch_id,
        "batch_dir": batch_dir.as_posix(),
        "cif_column": cif_column,
        "generated_count": len(generated_cifs),
        "failure_count": len(failures),
        "skipped_empty_rows": skipped_rows,
        "generated_cifs": generated_cifs,
        "failures": failures,
    }
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
            "cif_column": cif_column,
            "python_executable": sys.executable,
            "symprec": args.symprec,
            "angle_tolerance": args.angle_tolerance,
        },
    )

    print(f"batch_id={batch_id}")
    print(f"batch_dir={batch_dir.as_posix()}")
    print(f"manifest_path={manifest_path.as_posix()}")
    print(f"generated_count={len(generated_cifs)}")
    print(f"failure_count={len(failures)}")
    print(f"skipped_empty_rows={skipped_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())