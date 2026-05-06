"""External candidate structure preparation and de-duplication."""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class ExternalCifPreparationResult:
    manifest: dict[str, Any]
    cif_paths: list[Path]


@dataclass(frozen=True)
class StructureDuplicate:
    external_path: Path
    matched_path: Path
    matched_source: str


@dataclass(frozen=True)
class StructureDeduplicationResult:
    kept_external_paths: list[Path]
    duplicates: list[StructureDuplicate]
    parse_failures: list[dict[str, str]]


def configure_csv_field_size_limit() -> None:
    limit = sys.maxsize
    while limit > 0:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


def detect_cif_column(fieldnames: Iterable[str], override: str | None = None) -> str:
    names = list(fieldnames)
    if override:
        if override not in names:
            raise ValueError(f"Requested CIF column '{override}' not found in CSV header")
        return override

    cif_candidates = [name for name in names if "cif" in name.lower()]
    if not cif_candidates:
        raise ValueError("Could not detect a CIF column in the CSV header")

    return sorted(
        cif_candidates,
        key=lambda name: (
            "optimized" not in name.lower(),
            "cif" not in name.lower(),
            len(name),
        ),
    )[0]


def _slugify(text: str) -> str:
    import re

    lowered = text.lower().strip()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "external-cif"


def _sanitize_structure(structure, symprec: float, angle_tolerance: float):
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    analyzer = SpacegroupAnalyzer(structure, symprec=symprec, angle_tolerance=angle_tolerance)
    return analyzer.get_refined_structure(), analyzer.get_space_group_symbol(), analyzer.get_space_group_number()


def _export_structure(structure, output_path: Path) -> None:
    from pymatgen.io.cif import CifWriter

    output_path.parent.mkdir(parents=True, exist_ok=True)
    CifWriter(structure).write_file(output_path)


def prepare_external_cifs_from_csv(
    csv_path: Path | str,
    output_dir: Path | str,
    *,
    cif_column: str | None = None,
    id_column: str = "immutable_id",
    chemsys_column: str = "chemsys",
    symprec: float = 0.1,
    angle_tolerance: float = 5.0,
    limit: int | None = None,
) -> ExternalCifPreparationResult:
    """Extract CIF text from a CSV and write symmetrized CIF files.

    The CSV is expected to contain one column with CIF text. By default the
    column is auto-detected by looking for ``cif`` in the header and preferring
    optimized CIF columns.
    """

    from pymatgen.core import Structure

    configure_csv_field_size_limit()
    csv_path = Path(csv_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_cifs: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    skipped_rows = 0

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV header is missing")
        resolved_cif_column = detect_cif_column(reader.fieldnames, cif_column)

        for row_index, row in enumerate(reader, start=2):
            cif_text = (row.get(resolved_cif_column) or "").strip()
            if not cif_text:
                skipped_rows += 1
                continue

            immutable_id = (row.get(id_column) or f"row_{row_index}").strip()
            chemsys = (row.get(chemsys_column) or "").strip()
            stem = _slugify(immutable_id)

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
                exported_structure, symmetry_symbol, symmetry_number = _sanitize_structure(
                    structure,
                    symprec=symprec,
                    angle_tolerance=angle_tolerance,
                )
                symmetrized = True
            except Exception as exc:
                symmetry_error = str(exc)

            output_path = output_dir / f"{stem}.cif"
            _export_structure(exported_structure, output_path)
            generated_cifs.append(
                {
                    "row_index": row_index,
                    "immutable_id": immutable_id,
                    "chemsys": chemsys,
                    "status": "symmetrized" if symmetrized else "fallback_original_structure",
                    "symmetry_symbol": symmetry_symbol,
                    "symmetry_number": symmetry_number,
                    "symmetry_error": symmetry_error,
                    "cif_path": output_path.as_posix(),
                }
            )

            if limit is not None and len(generated_cifs) >= limit:
                break

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "csv_path": csv_path.as_posix(),
        "cif_column": resolved_cif_column,
        "output_dir": output_dir.as_posix(),
        "symprec": symprec,
        "angle_tolerance": angle_tolerance,
        "generated_count": len(generated_cifs),
        "failure_count": len(failures),
        "skipped_empty_rows": skipped_rows,
        "generated_cifs": generated_cifs,
        "failures": failures,
    }
    return ExternalCifPreparationResult(
        manifest=manifest,
        cif_paths=[Path(item["cif_path"]) for item in generated_cifs],
    )


def _load_structure(path: Path):
    from pymatgen.core import Structure

    return Structure.from_file(path)


def deduplicate_external_cifs(
    primary_paths: Iterable[Path | str],
    external_paths: Iterable[Path | str],
    *,
    external_source: str = "external",
    allow_subset: bool = False,
) -> StructureDeduplicationResult:
    """Remove external structures already represented by preferred candidates.

    ``primary_paths`` are preferred and are never removed. External candidates
    are compared against all primary structures and then against earlier kept
    external structures.
    """

    from pymatgen.analysis.structure_matcher import StructureMatcher

    matcher = StructureMatcher(allow_subset=allow_subset)
    parse_failures: list[dict[str, str]] = []
    preferred: list[tuple[Path, str, Any]] = []
    for raw_path in primary_paths:
        path = Path(raw_path)
        try:
            preferred.append((path, "preferred", _load_structure(path)))
        except Exception as exc:
            parse_failures.append({"path": path.as_posix(), "source": "preferred", "error": str(exc)})

    kept_external: list[Path] = []
    duplicates: list[StructureDuplicate] = []
    for raw_path in external_paths:
        path = Path(raw_path)
        try:
            structure = _load_structure(path)
        except Exception as exc:
            parse_failures.append({"path": path.as_posix(), "source": external_source, "error": str(exc)})
            continue

        match = next(
            (
                (existing_path, existing_source)
                for existing_path, existing_source, existing_structure in preferred
                if matcher.fit(existing_structure, structure)
            ),
            None,
        )
        if match is not None:
            duplicates.append(
                StructureDuplicate(
                    external_path=path,
                    matched_path=match[0],
                    matched_source=match[1],
                )
            )
            continue

        kept_external.append(path)
        preferred.append((path, external_source, structure))

    return StructureDeduplicationResult(
        kept_external_paths=kept_external,
        duplicates=duplicates,
        parse_failures=parse_failures,
    )
