#!/usr/bin/env python3
"""Merge multiple parquet indices into a single parquet/sqlite/json.gz file."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--parquets", nargs="+", required=True)
    p.add_argument("--out-parquet", type=Path, required=True)
    p.add_argument("--out-json", type=Path, required=False)
    p.add_argument("--out-sqlite", type=Path, required=False)
    args = p.parse_args()

    dfs = [pd.read_parquet(pq) for pq in args.parquets]
    
    # Normalize column types before merging
    numeric_cols = ['density', 'cell_volume', 'n_sites', 'nelements', 
                    'a', 'b', 'c', 'alpha', 'beta', 'gamma']
    for df in dfs:
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        # Ensure elements is a list (handle numpy arrays from parquet, JSON strings, etc.)
        if 'elements' in df.columns:
            import numpy as np
            def ensure_list(x):
                if isinstance(x, (list, np.ndarray)):
                    return list(x) if x is not None else []
                elif isinstance(x, str) and x.startswith('['):
                    try:
                        import json
                        return json.loads(x)
                    except:
                        return []
                else:
                    return []
            df['elements'] = df['elements'].apply(ensure_list)
    
    merged = pd.concat(dfs, ignore_index=True, sort=False)
    
    # Final cleanup: ensure elements column is true Python list (not numpy array) for parquet
    if 'elements' in merged.columns:
        import numpy as np
        merged['elements'] = merged['elements'].apply(
            lambda x: list(x) if isinstance(x, np.ndarray) else (x if isinstance(x, list) else [])
        )
    
    args.out_parquet.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(args.out_parquet, index=False)
    print("Wrote merged parquet:", args.out_parquet)

    if args.out_json:
        recs = merged.to_dict(orient="records")
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(args.out_json, "wt", encoding="utf-8") as fp:
            json.dump(recs, fp, ensure_ascii=False, separators=(",", ":"))
        print("Wrote merged json.gz:", args.out_json)

    if args.out_sqlite:
        import sqlite3

        args.out_sqlite.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(args.out_sqlite))
        
        # Prepare for SQLite: serialize list/dict columns to JSON strings
        merged_sql = merged.copy()
        for col in merged_sql.columns:
            if merged_sql[col].apply(lambda x: isinstance(x, (list, dict))).any():
                merged_sql[col] = merged_sql[col].apply(
                    lambda x: json.dumps(x) if isinstance(x, (list, dict)) else x
                )
        
        merged_sql.to_sql("index", conn, if_exists="replace", index=False)
        conn.close()
        print("Wrote merged sqlite:", args.out_sqlite)


if __name__ == "__main__":
    main()
