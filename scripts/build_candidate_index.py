#!/usr/bin/env python3
"""
Build and filter a candidate CIF index from multiple sources (ICSD CSV, MP pickle, COD CIF dir).

This script creates a gzipped JSON index compatible with DARA's StructureDatabase usage
and optionally copies/export selected CIF files into a destination folder for direct use
as additional_phases by DARA.

Key features:
- Support ICSD CSV summary files (detect common columns)
- Support Materials Project pandas pickle (attempts to export embedded Structure objects)
- Index COD folder by walking CIF files and extracting basic metadata via pymatgen
- Filtering by required/optional elements, density, and number of sites
- Outputs a gzipped JSON index with fields: id, source, path, formula, elements, density,
  cell_volume, n_sites, spacegroup

This file is intentionally added as a new script and does not modify existing code.
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from pymatgen.core import Composition, Structure
from pymatgen.io.cif import CifWriter
from tqdm import tqdm


COMMON_FORMULA_COLS = ["formula", "chemical_formula", "pretty_formula", "formula_pretty", "formula_sum"]
COMMON_ID_COLS = ["id", "icsd_id", "mp_id", "material_id", "entry_id", "structure_id"]
COMMON_DENSITY_COLS = ["density", "rho"]
COMMON_SPACEGROUP_COLS = ["spacegroup", "space_group", "sg"]
COMMON_PATH_COLS = ["cif_path", "file_path", "path"]


def parse_elements_from_formula(formula: str | None) -> list[str]:
    if not formula:
        return []
    try:
        comp = Composition(formula)
        return sorted([str(e) for e in comp.elements])
    except Exception:
        return []


def try_get_from_series(series: pd.Series, candidates: list[str]) -> Any:
    for c in candidates:
        if c in series and pd.notna(series[c]):
            return series[c]
    return None


def load_icsd(csv_path: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(csv_path, dtype=str, low_memory=False)
    records: list[dict[str, Any]] = []
    # normalize commonly-used column names if present (case-insensitive search)
    # prefer columns that include the word 'formula' (e.g., 'SumFormula')
    formula_col = next((c for c in df.columns if "formula" in c.lower()), None)
    if formula_col and "formula" not in df.columns:
        df["formula"] = df[formula_col]

    # density columns (CalculatedDensity, MeasuredDensity etc.)
    density_col = next((c for c in df.columns if "density" in c.lower()), None)
    if density_col and "density" not in df.columns:
        df["density"] = df[density_col]

    # id column fallback
    id_col = next((c for c in df.columns if c.lower() in ("id", "collectioncode", "icsd_id")), None)
    if id_col and "id" not in df.columns:
        df["id"] = df[id_col]

    # detect if the CSV contains an inline CIF text column named 'cif'
    has_inline_cif = "cif" in df.columns
    for idx, row in df.iterrows():
        formula = try_get_from_series(row, COMMON_FORMULA_COLS) or None
        elems = parse_elements_from_formula(formula)
        rec = {
            "id": try_get_from_series(row, COMMON_ID_COLS) or str(idx),
            "source": "ICSD",
            "formula": formula,
            "elements": elems,
            "density": try_get_from_series(row, COMMON_DENSITY_COLS),
            "cell_volume": None,
            "n_sites": None,
            "spacegroup": try_get_from_series(row, COMMON_SPACEGROUP_COLS),
            "path": try_get_from_series(row, COMMON_PATH_COLS),
        }
        # If the CSV contains inline CIF text, store it as a temporary file path if possible
        if has_inline_cif:
            try:
                cif_text = row.get("cif") if isinstance(row, dict) else row.get("cif")
            except Exception:
                cif_text = None
            if cif_text and isinstance(cif_text, str) and cif_text.strip():
                # write to a temporary file (will be moved later if export requested)
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".cif")
                try:
                    tmp.write(cif_text.encode("utf-8"))
                    tmp.close()
                    rec["path"] = str(Path(tmp.name).resolve())
                except Exception:
                    try:
                        tmp.close()
                    except Exception:
                        pass
        records.append(rec)
    return records


def load_mp(pkl_path: Path, export_cif_dir: Path | None = None) -> list[dict[str, Any]]:
    df = pd.read_pickle(pkl_path)
    records: list[dict[str, Any]] = []

    # prepare export dir
    if export_cif_dir is not None:
        export_cif_dir.mkdir(parents=True, exist_ok=True)

    for idx, row in df.iterrows():
        rec = {"source": "MP", "id": None, "formula": None, "elements": [], "density": None, "cell_volume": None, "n_sites": None, "spacegroup": None, "path": None}

        # row may be a Series or dict-like
        try:
            # id
            rec["id"] = try_get_from_series(row, COMMON_ID_COLS) or str(idx)
        except Exception:
            rec["id"] = str(idx)

        try:
            rec["formula"] = try_get_from_series(row, COMMON_FORMULA_COLS) or (row.get("pretty_formula") if isinstance(row, dict) else None)
        except Exception:
            rec["formula"] = None

        rec["elements"] = parse_elements_from_formula(rec["formula"]) if rec["formula"] else []

        try:
            rec["density"] = try_get_from_series(row, COMMON_DENSITY_COLS)
        except Exception:
            rec["density"] = None

        # attempt to find a Structure and export to CIF if possible
        structure_obj = None
        if isinstance(row, dict):
            for k in ("structure", "structure_obj", "structure_dict"):
                if k in row and row[k] is not None:
                    structure_obj = row[k]
                    break
        else:
            # pandas Series
            for k in ("structure", "structure_obj", "structure_dict"):
                if k in row.index and row[k] is not None:
                    structure_obj = row[k]
                    break

        s: Structure | None = None
        try:
            if isinstance(structure_obj, Structure):
                s = structure_obj
            elif isinstance(structure_obj, dict):
                try:
                    s = Structure.from_dict(structure_obj)
                except Exception:
                    s = None
        except Exception:
            s = None

        if s is not None:
            rec["n_sites"] = len(s)
            rec["cell_volume"] = s.volume
            rec["density"] = rec["density"] or s.density
            try:
                sg = s.get_space_group_info()
                rec["spacegroup"] = sg[0] if sg else None
            except Exception:
                rec["spacegroup"] = None

            if export_cif_dir is not None:
                out = export_cif_dir / f"MP_{rec['id']}.cif"
                try:
                    CifWriter(s).write_file(str(out))
                    rec["path"] = str(out.resolve())
                except Exception:
                    rec["path"] = None

        records.append(rec)
    return records


def index_cod(cod_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for cif in tqdm(list(Path(cod_dir).rglob("*.cif")), desc="Index COD"):
        try:
            s = Structure.from_file(str(cif))
        except Exception:
            continue
        rec = {
            "id": cif.stem,
            "source": "COD",
            "formula": str(s.composition.reduced_formula),
            "elements": sorted([str(e) for e in s.composition.elements]),
            "density": s.density,
            "cell_volume": s.volume,
            "n_sites": len(s),
            "spacegroup": None,
            "path": str(cif.resolve()),
        }
        try:
            sg = s.get_space_group_info()
            rec["spacegroup"] = sg[0] if sg else None
        except Exception:
            rec["spacegroup"] = None
        records.append(rec)
    return records


def filter_records(records: list[dict[str, Any]], required: list[str], optional: list[str], min_density: float | None, max_density: float | None, min_sites: int | None, max_sites: int | None) -> list[dict[str, Any]]:
    req = set([e.capitalize() for e in required]) if required else set()
    opt = set([e.capitalize() for e in optional]) if optional else set()
    out: list[dict[str, Any]] = []
    for r in records:
        elems = set([e.capitalize() for e in r.get("elements", [])])
        if req and not req.issubset(elems):
            continue
        if opt and elems.isdisjoint(opt):
            # if optional provided, require at least one optional present
            continue
        dens = r.get("density")
        try:
            if dens is not None:
                dens_val = float(dens)
            else:
                dens_val = None
        except Exception:
            dens_val = None
        if dens_val is not None:
            if min_density is not None and dens_val < min_density:
                continue
            if max_density is not None and dens_val > max_density:
                continue
        nsites = r.get("n_sites")
        try:
            if nsites is not None:
                nsites_val = int(nsites)
            else:
                nsites_val = None
        except Exception:
            nsites_val = None
        if nsites_val is not None:
            if min_sites is not None and nsites_val < min_sites:
                continue
            if max_sites is not None and nsites_val > max_sites:
                continue
        out.append(r)
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Build filtered CIF index for DARA from ICSD/MP/COD")
    p.add_argument("--icsd-csv", type=Path, help="ICSD summary CSV path")
    p.add_argument("--mp-pkl", type=Path, help="Materials Project pandas pickle")
    p.add_argument("--cod-dir", type=Path, help="COD CIF root directory (unzipped)")
    p.add_argument("--use-icsd", action="store_true")
    p.add_argument("--use-mp", action="store_true")
    p.add_argument("--use-cod", action="store_true")
    p.add_argument("--required-elements", type=str, default="", help="Comma-separated required elements, e.g. Li,Fe,O")
    p.add_argument("--optional-elements", type=str, default="", help="Comma-separated optional elements; if provided at least one must match")
    p.add_argument("--min-density", type=float, default=None)
    p.add_argument("--max-density", type=float, default=None)
    p.add_argument("--min-sites", type=int, default=None)
    p.add_argument("--max-sites", type=int, default=None)
    p.add_argument("--out-index", type=Path, default=Path("filtered_index.json.gz"))
    p.add_argument("--export-cif-dir", type=Path, default=None, help="Copy filtered CIFs to this directory")
    args = p.parse_args()

    required = [x.strip() for x in args.required_elements.split(",") if x.strip()]
    optional = [x.strip() for x in args.optional_elements.split(",") if x.strip()]

    all_records: list[dict[str, Any]] = []
    tmp_export_dir: Path | None = None

    if args.use_icsd and args.icsd_csv:
        print("Loading ICSD CSV...")
        all_records += load_icsd(args.icsd_csv)

    if args.use_mp and args.mp_pkl:
        print("Loading MP pickle...")
        export_dir = args.export_cif_dir or Path(tempfile.mkdtemp(prefix="mp_cif_export_"))
        all_records += load_mp(args.mp_pkl, export_dir)
        if args.export_cif_dir is None:
            tmp_export_dir = export_dir

    if args.use_cod and args.cod_dir:
        print("Indexing COD directory (this may take a while)...")
        all_records += index_cod(args.cod_dir)

    print(f"Total records loaded: {len(all_records)}")
    filtered = filter_records(all_records, required, optional, args.min_density, args.max_density, args.min_sites, args.max_sites)
    print(f"Filtered -> {len(filtered)} records")

    # optionally copy cif files to export dir for DARA convenience
    if args.export_cif_dir:
        args.export_cif_dir.mkdir(parents=True, exist_ok=True)
        for r in tqdm(filtered, desc="Copy CIFs"):
            path = r.get("path")
            if path:
                try:
                    shutil.copy(path, args.export_cif_dir)
                    r["path"] = str((args.export_cif_dir / Path(path).name).resolve())
                except Exception:
                    # ignore copy errors but keep record
                    pass

    # write gzipped json
    args.out_index.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(args.out_index, "wt", encoding="utf-8") as fp:
        json.dump(filtered, fp, ensure_ascii=False, separators=(",", ":"))
    print("Wrote index ->", args.out_index)

    # cleanup temporary export if used
    if tmp_export_dir:
        try:
            shutil.rmtree(tmp_export_dir)
        except Exception:
            pass


if __name__ == "__main__":
    main()
