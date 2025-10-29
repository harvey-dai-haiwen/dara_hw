#!/usr/bin/env python
"""Quick verification of cod/icsd index files - prints metadata and samples."""
import os
import sys

def verify_parquet(path):
    """Check parquet file metadata."""
    try:
        import pyarrow.parquet as pq
        if not os.path.exists(path):
            print(f"❌ {path} NOT FOUND")
            return False
        pf = pq.ParquetFile(path)
        rows = pf.metadata.num_rows
        cols = [c.name for c in pf.schema_arrow]
        print(f"✓ {path}")
        print(f"  Rows: {rows:,}")
        print(f"  Columns: {cols[:10]}{'...' if len(cols) > 10 else ''}")
        return True
    except Exception as e:
        print(f"❌ {path} error: {e}")
        return False

def verify_sqlite(path):
    """Check sqlite file metadata."""
    try:
        import sqlite3
        if not os.path.exists(path):
            print(f"❌ {path} NOT FOUND")
            return False
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
        row = cur.fetchone()
        if not row:
            print(f"❌ {path} has no tables")
            conn.close()
            return False
        table = row[0]
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"✓ {path}")
        print(f"  Table: {table}, Rows: {count:,}")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ {path} error: {e}")
        return False

def print_sample(path, n=5):
    """Print first n records from parquet."""
    try:
        import pandas as pd
        if not os.path.exists(path):
            return
        df = pd.read_parquet(path, engine='pyarrow')
        print(f"\n📋 Sample from {path} (first {n} rows):")
        # Print key columns only
        key_cols = [c for c in ['id', 'source', 'formula', 'elements', 'spacegroup', 'path'] if c in df.columns]
        print(df[key_cols].head(n).to_string(index=False))
    except Exception as e:
        print(f"Sample error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("INDEX VERIFICATION")
    print("=" * 60)
    
    # Check file sizes first
    print("\n📂 File sizes:")
    for pattern in ["indexes/*cod*", "indexes/*icsd*"]:
        import glob
        for f in glob.glob(pattern):
            if os.path.isfile(f):
                size_mb = os.path.getsize(f) / 1024 / 1024
                print(f"  {os.path.basename(f)}: {size_mb:.1f} MB")
    
    print("\n" + "=" * 60)
    print("PARQUET FILES")
    print("=" * 60)
    verify_parquet("indexes/cod_index.parquet")
    verify_parquet("indexes/icsd_index.parquet")
    
    print("\n" + "=" * 60)
    print("SQLITE FILES")
    print("=" * 60)
    verify_sqlite("indexes/cod_index.sqlite")
    verify_sqlite("indexes/icsd_index.sqlite")
    
    print("\n" + "=" * 60)
    print("SAMPLES")
    print("=" * 60)
    print_sample("indexes/cod_index.parquet", 3)
    print_sample("indexes/icsd_index.parquet", 3)
    
    print("\n✅ Verification complete")
