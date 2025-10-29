#!/usr/bin/env python3
"""Index ICSD CSV into Parquet + SQLite with unified schema.

Reads the ICSD CSV, normalizes columns, attempts to parse inline CIFs (if present)
or parse files referenced by path. Writes a parquet and optional sqlite database.
"""
from __future__ import annotations

import argparse
import gzip
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from pymatgen.core import Composition, Structure
from pymatgen.io.cif import CifParser
from tqdm import tqdm


COMMON_FORMULA_COLS = ["formula", "chemical_formula", "pretty_formula", "formula_pretty", "SumFormula", "SumFormula"]


def parse_elements_from_formula(formula: str | None) -> List[str]:
    if not formula:
        return []
    try:
        comp = Composition(formula)
        return sorted([str(e) for e in comp.elements])
    except Exception:
        return []


def try_normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # map some known ICSD headers to our canonical names
    for c in df.columns:
        lc = c.lower()
        if "formula" in lc and "formula" not in df.columns:
            df["formula"] = df[c]
        if "density" in lc and "density" not in df.columns:
            df["density"] = df[c]
        if lc in ("collectioncode", "id") and "id" not in df.columns:
            df["id"] = df[c]
    return df


def parse_inline_cif_and_extract(cif_text: str) -> Dict[str, Any] | None:
    try:
        parser = CifParser.from_string(cif_text)
        s = parser.get_structures()[0]
        lat = s.lattice
        elems = sorted([str(e) for e in s.composition.elements])
        return {
            "formula": str(s.composition.reduced_formula),
            "elements": elems,
            "nelements": len(elems),
            "n_sites": len(s),
            "density": s.density,
            "cell_volume": s.volume,
            "a": lat.a,
            "b": lat.b,
            "c": lat.c,
            "alpha": lat.alpha,
            "beta": lat.beta,
            "gamma": lat.gamma,
        }
    except Exception:
        return None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--icsd-csv", type=Path, required=True)
    p.add_argument("--out-parquet", type=Path, required=True)
    p.add_argument("--out-sqlite", type=Path, required=False)
    p.add_argument("--parse-inline-cif", action="store_true")
    p.add_argument("--sample", type=int, default=0, help="If >0 only process first N rows (dry-run)")
    args = p.parse_args()

    df = pd.read_csv(args.icsd_csv, dtype=str, low_memory=False)
    df = try_normalize_columns(df)
    if args.sample and args.sample > 0:
        df = df.iloc[: args.sample]

    rows: List[Dict[str, Any]] = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="ICSD rows"):
        rec: Dict[str, Any] = {}
        rec["source"] = "ICSD"
        rec["raw_db_id"] = row.get("id") if "id" in row else None
        rec["path"] = row.get("cif_path") if "cif_path" in row else None
        rec["formula"] = row.get("formula") if "formula" in row else None
        rec["elements"] = parse_elements_from_formula(rec["formula"]) if rec["formula"] else []
        rec["nelements"] = len(rec["elements"]) if rec["elements"] else None
        rec["n_sites"] = None
        rec["density"] = row.get("density") if "density" in row else None
        rec["cell_volume"] = row.get("CellVolume") if "CellVolume" in row else None
        rec["a"] = rec["b"] = rec["c"] = rec["alpha"] = rec["beta"] = rec["gamma"] = None
        rec["crystal_system"] = None
        rec["spacegroup"] = None
        rec["extra"] = {}

        # attempt to parse inline CIF if requested and present
        if args.parse_inline_cif and "cif" in row and isinstance(row.get("cif"), str) and row.get("cif").strip():
            info = parse_inline_cif_and_extract(row.get("cif"))
            if info:
                rec.update(info)

        rows.append(rec)

    df_out = pd.DataFrame(rows)
    args.out_parquet.parent.mkdir(parents=True, exist_ok=True)
    # try to write parquet, fall back to gzipped JSON if pyarrow/fastparquet not available
    try:
        df_out.to_parquet(args.out_parquet, index=False)
        print("Wrote parquet:", args.out_parquet)
    except Exception as e:
        print("Parquet write failed (pyarrow/fastparquet may be missing). Falling back to JSON.gz. Error:", e)
        out_json = args.out_parquet.with_suffix(".json.gz")
        out_json.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(out_json, "wt", encoding="utf-8") as fp:
            json.dump(df_out.to_dict(orient="records"), fp, ensure_ascii=False, separators=(",", ":"))
        print("Wrote gzipped json fallback:", out_json)

    if args.out_sqlite:
        import sqlite3

        args.out_sqlite.parent.mkdir(parents=True, exist_ok=True)
        # sqlite doesn't accept Python lists; serialize list/complex columns to JSON strings
        df_sql = df_out.copy()
        def _serialize(x):
            import pandas as _pd
            # handle NaN-like
            try:
                if _pd.isna(x):
                    return None
            except Exception:
                pass
            # lists/dicts -> json
            if isinstance(x, (list, dict)):
                return json.dumps(x, ensure_ascii=False)
            # numpy arrays or similar -> convert to list
            try:
                if hasattr(x, "tolist") and not isinstance(x, (str, bytes)):
                    return json.dumps(x.tolist(), ensure_ascii=False)
            except Exception:
                pass
            return x

        if "elements" in df_sql.columns:
            df_sql["elements"] = df_sql["elements"].apply(_serialize)
        if "extra" in df_sql.columns:
            df_sql["extra"] = df_sql["extra"].apply(_serialize)

        conn = sqlite3.connect(str(args.out_sqlite))
        df_sql.to_sql("icsd_index", conn, if_exists="replace", index=False)
        conn.close()
        print("Wrote sqlite:", args.out_sqlite)


if __name__ == "__main__":
    main()
