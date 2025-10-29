#!/usr/bin/env python3
"""Parallel COD CIF indexer (writes Parquet shards and optional SQLite).

Usage:
  python scripts/index_cod_parallel.py --cod-dir <extracted_cod_dir> --out-parquet indexes/cod_index.parquet --workers 12 --chunk-size 500

This script walks the COD directory for .cif files, parses them in parallel using
pymatgen, writes per-shard parquet files and merges them into a final parquet and
optionally a sqlite database. Designed to be robust for large datasets.
"""
from __future__ import annotations

import argparse
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from pymatgen.core import Structure
from tqdm import tqdm


def parse_cif(path: str) -> Dict[str, Any]:
    try:
        s = Structure.from_file(path)
        lat = s.lattice
        elems = sorted([str(e) for e in s.composition.elements])
        return {
            "id": Path(path).stem,
            "source": "COD",
            "raw_db_id": Path(path).stem,
            "path": str(path),
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
            "crystal_system": None,
            "spacegroup": None,
            "extra": None,
        }
    except Exception as e:
        return {"id": Path(path).stem, "source": "COD", "path": str(path), "error": str(e)}


def worker_parse(paths: List[str], out_parquet: str) -> str:
    rows = []
    for p in paths:
        rows.append(parse_cif(p))
    df = pd.DataFrame(rows)
    df.to_parquet(out_parquet, index=False)
    return out_parquet


def chunked(it: List[str], n: int):
    for i in range(0, len(it), n):
        yield it[i : i + n]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--cod-dir", type=Path, required=True)
    p.add_argument("--out-parquet", type=Path, required=True)
    p.add_argument("--out-sqlite", type=Path, required=False)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--chunk-size", type=int, default=1000)
    p.add_argument("--dry-run", action="store_true", help="Parse only first chunk and exit")
    args = p.parse_args()

    files = [str(p) for p in args.cod_dir.rglob("*.cif")]
    if not files:
        print("No CIF files found in", args.cod_dir)
        return

    if args.dry_run:
        files = files[: args.chunk_size]

    tmpdir = Path(tempfile.mkdtemp(prefix="cod_index_"))
    shards: List[str] = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futures = []
        for i, chunk in enumerate(chunked(files, args.chunk_size)):
            out_shard = tmpdir / f"shard_{i}.parquet"
            futures.append(ex.submit(worker_parse, chunk, str(out_shard)))
        for fut in tqdm(futures, desc="parsing shards"):
            try:
                shard = fut.result()
                shards.append(shard)
            except Exception as e:
                print("Shard failed:", e)

    # merge shards
    dfs = [pd.read_parquet(s) for s in shards]
    combined = pd.concat(dfs, ignore_index=True, sort=False)
    args.out_parquet.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(args.out_parquet, index=False)
    print("Wrote parquet:", args.out_parquet)

    if args.out_sqlite:
        import sqlite3

        args.out_sqlite.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(args.out_sqlite))
        combined.to_sql("cod_index", conn, if_exists="replace", index=False)
        conn.close()
        print("Wrote sqlite:", args.out_sqlite)


if __name__ == "__main__":
    main()
