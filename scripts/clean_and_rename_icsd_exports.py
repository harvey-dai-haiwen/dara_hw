#!/usr/bin/env python3
"""Copy and rename ICSD CIF exports into a clean directory and update the gzipped index.

Usage:
  python scripts/clean_and_rename_icsd_exports.py --index filtered_index_icsd_fe.json.gz --out-index filtered_index_icsd_fe_clean.json.gz --out-dir filtered_cifs_icsd_fe_clean

This script will:
 - read the provided gzipped JSON index
 - for each record with source == 'ICSD' and a valid path, copy the file into the clean out-dir
 - rename files to ICSD_<id>.cif (sanitize id), avoiding name collisions by appending a counter
 - update the 'path' field in the index records to point to the new file
 - write a new gzipped JSON index
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
from pathlib import Path
from typing import Any


def sanitize_filename(s: str) -> str:
    # basic sanitization for filesystem-safe names
    keep = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return ''.join(c if c in keep else '_' for c in s).replace(' ', '_')


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--out-index", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()

    if not args.index.exists():
        print("Index file not found:", args.index)
        return 2

    args.out_dir.mkdir(parents=True, exist_ok=True)

    with gzip.open(args.index, "rt", encoding="utf-8") as fp:
        records = json.load(fp)

    moved = 0
    for rec in records:
        try:
            if rec.get("source") != "ICSD":
                continue
            old_path = rec.get("path")
            if not old_path:
                continue
            oldp = Path(old_path)
            if not oldp.exists():
                # try resolving relative to repo
                alt = Path(old_path)
                if not alt.exists():
                    continue
                oldp = alt

            idstr = str(rec.get("id") or "unknown")
            base = f"ICSD_{sanitize_filename(idstr)}.cif"
            dest = args.out_dir / base
            # avoid collisions
            counter = 1
            while dest.exists():
                dest = args.out_dir / f"ICSD_{sanitize_filename(idstr)}_{counter}.cif"
                counter += 1

            shutil.copy2(str(oldp), str(dest))
            rec["path"] = str(dest.resolve())
            moved += 1
        except Exception:
            # ignore individual failures but continue
            continue

    with gzip.open(args.out_index, "wt", encoding="utf-8") as fp:
        json.dump(records, fp, ensure_ascii=False, separators=(",", ":"))

    print(f"Processed records: {len(records)}, ICSD files moved: {moved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
