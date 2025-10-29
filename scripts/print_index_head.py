#!/usr/bin/env python3
"""Print a short summary (count + head) of a gzipped JSON index created by build_candidate_index.py"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: print_index_head.py <index.json.gz> [n]")
        return 2
    p = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    if not p.exists():
        print(f"File not found: {p}")
        return 1
    with gzip.open(p, "rt", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Total records: {len(data)}")
    print(f"Showing first {n} entries:")
    for i, r in enumerate(data[:n]):
        print(i + 1, json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
