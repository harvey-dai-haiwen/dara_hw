#!/usr/bin/env python3
"""Convert the ICSD JSON.gz index to Parquet, normalizing types so pyarrow can write it.

Reads: indexes/icsd_index.json.gz
Writes: indexes/icsd_index.parquet
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    in_path = Path("indexes/icsd_index.json.gz")
    out_path = Path("indexes/icsd_index.parquet")
    if not in_path.exists():
        print("Input not found:", in_path)
        return
    with gzip.open(in_path, "rt", encoding="utf-8") as fp:
        records = json.load(fp)
    # normalize
    for r in records:
        # elements -> list (or empty list)
        if "elements" not in r or r["elements"] is None:
            r["elements"] = []
        # extra -> JSON string or None
        if "extra" in r:
            if r["extra"] is None:
                r["extra"] = None
            else:
                try:
                    r["extra"] = json.dumps(r["extra"], ensure_ascii=False)
                except Exception:
                    r["extra"] = str(r["extra"])
        else:
            r["extra"] = None
        # numeric conversions
        if "nelements" in r and r["nelements"] is not None:
            try:
                r["nelements"] = int(float(r["nelements"]))
            except Exception:
                r["nelements"] = None
    df = pd.DataFrame(records)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    print("Wrote parquet:", out_path)


if __name__ == "__main__":
    main()
