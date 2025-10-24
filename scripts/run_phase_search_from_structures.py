#!/usr/bin/env python3
"""
Run DARA PhaseSearch using in-memory pymatgen Structure objects or an index produced
by `build_candidate_index.py`.

This script attempts to prefer DARA's internal CIF/structure handling:
- If provided with a gzipped JSON index (filtered_index.json.gz), it will load the
  records and construct `dara.cif.Cif` objects by reading existing CIF paths when
  available.
- If provided with a Materials Project pickle which contains pymatgen Structure
  objects, it will convert those Structures to `dara.cif.Cif` using
  `dara.cif.Cif.from_structure` (this reuses DARA's CIF conversion and naming logic).

The script does not modify existing DARA source files. It wraps DARA's
`PhaseSearchMaker` so you can pass Structure-derived CIF objects directly.

Note: DARA's PhaseSearchMaker will still write CIF files under a working
directory for the job; this script avoids the user having to write CIFs manually.
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any, cast

import pandas as pd

from dara.cif import Cif
from dara.jobs import PhaseSearchMaker
from dara.xrd import XYFile


def load_index(index_path: Path) -> list[dict[str, Any]]:
    with gzip.open(index_path, "rt", encoding="utf-8") as fp:
        return json.load(fp)


def build_cif_objects_from_index(index_records: list[dict[str, Any]]) -> list[Cif]:
    cifs: list[Cif] = []
    for rec in index_records:
        path = rec.get("path")
        if path:
            try:
                c = Cif.from_file(Path(path))
                # ensure we have a Cif object
                c = cast(Cif, c)
                cifs.append(c)
                continue
            except Exception:
                # fallback to trying to use formula/name only
                pass
        # no disk CIF available; try to build minimal CIF with formula as name
        # create an empty Cif wrapper to preserve interface (best-effort)
        try:
            # create a minimal CIF string using the formula field if present
            formula = rec.get("formula") or rec.get("id")
            if formula:
                # create a tiny dummy CIF block to satisfy PhaseSearchMaker writing logic
                cif_str = f"data_{formula}\n# dummy CIF generated from index"
                c = cast(Cif, Cif.from_str(cif_str))
                # prefer to set the filename attribute for provenance
                try:
                    c.filename = rec.get("id") or formula
                except Exception:
                    # ignore if attribute not writable in some unexpected subclass
                    pass
                cifs.append(c)
        except Exception:
            continue
    return cifs


def load_mp_and_convert(pkl_path: Path) -> list[Cif]:
    df = pd.read_pickle(pkl_path)
    cifs: list[Cif] = []
    for idx, row in df.iterrows():
        structure_obj = None
        if isinstance(row, dict):
            structure_obj = row.get("structure") or row.get("structure_obj")
        else:
            for k in ("structure", "structure_obj"):
                if k in row.index and row[k] is not None:
                    structure_obj = row[k]
                    break

        if structure_obj is None:
            continue

        try:
            # If it's a dict, try to reconstruct Structure
            if isinstance(structure_obj, dict):
                from pymatgen.core import Structure as PMStructure

                s = PMStructure.from_dict(structure_obj)
            else:
                s = structure_obj

            c = Cif.from_structure(s, filename=str(idx))
            cifs.append(c)
        except Exception:
            continue

    return cifs


def main() -> None:
    p = argparse.ArgumentParser(description="Run phase search from in-memory Structures or index")
    p.add_argument("--pattern", type=Path, required=True, help="Path to pattern (.xy/.xrdml)")
    p.add_argument("--index", type=Path, help="Gzipped JSON index produced by build_candidate_index.py")
    p.add_argument("--mp-pkl", type=Path, help="Materials Project pandas pickle (optional) to convert Structures from)")
    p.add_argument("--use-index", action="store_true")
    p.add_argument("--use-mp", action="store_true")
    p.add_argument("--max-num-results", type=int, default=5)
    p.add_argument("--cifs-folder-name", type=str, default="dara_cifs")
    args = p.parse_args()

    xrd = XYFile.from_file(args.pattern)

    candidate_cifs: list[Cif] = []
    if args.use_index and args.index:
        recs = load_index(args.index)
        candidate_cifs += build_cif_objects_from_index(recs)

    if args.use_mp and args.mp_pkl:
        candidate_cifs += load_mp_and_convert(args.mp_pkl)

    if not candidate_cifs:
        raise SystemExit("No candidate CIFs found from provided inputs.")

    # instantiate PhaseSearchMaker and run
    psm = PhaseSearchMaker()
    # set maker attributes (these are dataclass fields on the Maker)
    try:
        psm.max_num_results = args.max_num_results
    except Exception:
        pass
    try:
        psm.cifs_folder_name = args.cifs_folder_name
    except Exception:
        pass

    # PhaseSearchMaker.make expects an XRDData and list[Cif] when cifs provided
    result = psm.make(xrd_data=xrd, cifs=candidate_cifs)

    # print brief summary
    try:
        print("Phase search finished. Best Rwp:", result.best_rwp)
    except Exception:
        print("Phase search finished.")
    # print number of returned results if available
    try:
        if getattr(result, "results", None) is not None:
            nres = len(result.results)  # type: ignore[arg-type]
            print(f"Number of returned results: {nres}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
