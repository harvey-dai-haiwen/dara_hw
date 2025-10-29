#!/usr/bin/env python3
"""Dry-run: read first N .cif files from a COD tar and try to parse them with pymatgen.
Useful to validate tar structure before full extraction/indexing.
"""
from __future__ import annotations

import argparse
import tarfile
from pathlib import Path
from typing import List

from pymatgen.io.cif import CifParser


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--tar", type=Path, required=True)
    p.add_argument("--n", type=int, default=50)
    args = p.parse_args()

    count = 0
    parsed = 0
    errors = 0
    with tarfile.open(args.tar, "r") as tf:
        members = [m for m in tf.getmembers() if m.name.lower().endswith('.cif')]
        print(f"Found {len(members)} CIF members (listing). Will try first {min(args.n, len(members))}.")
        for m in members[: args.n]:
            try:
                f = tf.extractfile(m)
                if f is None:
                    errors += 1
                    continue
                data = f.read().decode('utf-8', errors='ignore')
                # some pymatgen versions don't provide CifParser.from_string; use file-like object
                from io import StringIO

                try:
                    parser = CifParser(StringIO(data))
                    structs = parser.get_structures()
                    if structs:
                        parsed += 1
                except Exception:
                    # fallback: write to temp file and try
                    import tempfile

                    with tempfile.NamedTemporaryFile('w', suffix='.cif', delete=True, encoding='utf-8') as tmp:
                        tmp.write(data)
                        tmp.flush()
                        try:
                            parser = CifParser(tmp.name)
                            structs = parser.get_structures()
                            if structs:
                                parsed += 1
                        except Exception:
                            errors += 1
                            continue
            except Exception as e:
                errors += 1
            count += 1

    print(f"Tried: {count}, Parsed: {parsed}, Errors: {errors}")


if __name__ == '__main__':
    main()
