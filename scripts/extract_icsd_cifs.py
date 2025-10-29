#!/usr/bin/env python3
"""
Extract CIF files from ICSD CSV and fill spacegroup information.

This script:
1. Reads ICSD CSV containing inline CIF data
2. Extracts CIF content to individual files
3. Parses each CIF to extract spacegroup using pymatgen
4. Updates the ICSD index with file paths and spacegroup info

Usage:
    # Process all ICSD entries
    python extract_icsd_cifs.py --csv path/to/icsd.csv --index icsd_index.parquet \
        --cif-dir icsd_cifs --out icsd_index_filled.parquet
    
    # Test with first 100 entries
    python extract_icsd_cifs.py --csv path/to/icsd.csv --index icsd_index.parquet \
        --cif-dir icsd_cifs --out icsd_index_test.parquet --sample 100
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from tqdm import tqdm
from pymatgen.io.cif import CifParser
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


def extract_and_parse_cif(row, cif_dir, collection_code):
    """
    Extract CIF from CSV row, save to file, and parse spacegroup.
    
    Args:
        row: DataFrame row with 'cif' column
        cif_dir: Base directory for CIF files
        collection_code: ICSD CollectionCode (from index or passed separately)
        
    Returns:
        tuple: (cif_path_relative, spacegroup_symbol) or (None, None) on failure
    """
    cif_content = row['cif']
    
    # Skip if no CIF content
    if pd.isna(cif_content) or not isinstance(cif_content, str) or len(cif_content) < 10:
        return None, None
    
    try:
        # Create directory structure like COD: cif/1/23/45/1234567.cif
        # For ICSD CollectionCode (e.g., 12345), create cif/1/23/45/12345.cif
        code_str = str(collection_code).zfill(7)  # Pad to 7 digits
        subdir1 = code_str[0]
        subdir2 = code_str[1:3]
        subdir3 = code_str[3:5]
        
        cif_subdir = Path(cif_dir) / "cif" / subdir1 / subdir2 / subdir3
        cif_subdir.mkdir(parents=True, exist_ok=True)
        
        cif_filename = f"{collection_code}.cif"
        cif_path = cif_subdir / cif_filename
        
        # Write CIF content to file
        with open(cif_path, 'w', encoding='utf-8') as f:
            f.write(cif_content)
        
        # Parse spacegroup
        try:
            parser = CifParser(str(cif_path))
            structures = parser.parse_structures(primitive=False)
            
            if structures:
                struct = structures[0]  # Take first structure
                sga = SpacegroupAnalyzer(struct)
                sg_symbol = sga.get_space_group_symbol()
                
                # Return relative path - cif_path is already relative if cif_dir is relative
                # Convert to forward slashes for cross-platform compatibility
                return str(cif_path).replace('\\', '/'), sg_symbol
            else:
                return str(cif_path).replace('\\', '/'), None
                
        except Exception as e:
            # CIF file created but parsing failed
            return str(cif_path).replace('\\', '/'), None
    
    except Exception as e:
        return None, None


def main():
    parser = argparse.ArgumentParser(description='Extract ICSD CIFs and fill spacegroup')
    parser.add_argument('--csv', required=True, help='Path to ICSD CSV file')
    parser.add_argument('--index', required=True, help='Path to ICSD parquet index')
    parser.add_argument('--cif-dir', required=True, help='Directory to store extracted CIFs')
    parser.add_argument('--out', required=True, help='Output parquet file with updated paths/spacegroups')
    parser.add_argument('--sample', type=int, default=None, help='Process only first N records (for testing)')
    
    args = parser.parse_args()
    
    # Load ICSD index
    print(f"📖 Loading ICSD index from {args.index}...")
    df_index = pd.read_parquet(args.index)
    total_records = len(df_index)
    print(f"  Total records in index: {total_records:,}")
    
    # Load ICSD CSV (only needed columns)
    print(f"\n📖 Loading ICSD CSV from {args.csv}...")
    print("  (Only loading CollectionCode and cif columns)")
    
    # Use chunks to handle large CSV efficiently
    if args.sample:
        df_csv = pd.read_csv(args.csv, usecols=['CollectionCode', 'cif'], nrows=args.sample)
        print(f"  Loaded first {args.sample:,} rows (sample mode)")
    else:
        df_csv = pd.read_csv(args.csv, usecols=['CollectionCode', 'cif'])
        print(f"  Loaded {len(df_csv):,} rows")
    
    # Convert CollectionCode to string to match raw_db_id
    df_csv['CollectionCode'] = df_csv['CollectionCode'].astype(str)
    
    # Filter index to match CSV entries (in case sample mode)
    if args.sample:
        # Get CollectionCodes from CSV
        csv_codes = set(df_csv['CollectionCode'].values)
        df_index = df_index[df_index['raw_db_id'].isin(csv_codes)].copy()
        print(f"  Filtered index to {len(df_index):,} matching records")
    
    # Merge to get CIF content (on raw_db_id = CollectionCode)
    print(f"\n🔗 Merging index with CSV data...")
    df_csv_indexed = df_csv.set_index('CollectionCode')
    
    # Keep raw_db_id as column for processing
    df_merged = df_index.copy()
    df_merged = df_merged.join(df_csv_indexed, on='raw_db_id', how='inner')
    print(f"  Merged records: {len(df_merged):,}")
    
    # Process each entry
    print(f"\n🔧 Extracting CIFs and parsing spacegroups...")
    print(f"   Mode: Sequential processing (lower memory usage)")
    print(f"   Output directory: {args.cif_dir}")
    
    paths = []
    spacegroups = []
    
    for idx, row in tqdm(df_merged.iterrows(), total=len(df_merged), desc="Processing"):
        collection_code = row['raw_db_id']
        cif_path, sg = extract_and_parse_cif(row, args.cif_dir, collection_code)
        paths.append(cif_path)
        spacegroups.append(sg)
    
    # Update index
    print(f"\n📝 Updating index with paths and spacegroups...")
    df_merged['path'] = paths
    df_merged['spacegroup'] = spacegroups
    
    # Drop the 'cif' column (we don't need it in the index anymore)
    if 'cif' in df_merged.columns:
        df_merged = df_merged.drop(columns=['cif'])
    
    # Statistics
    updated = sum(1 for p in paths if p is not None)
    failed = sum(1 for p in paths if p is None)
    with_sg = sum(1 for sg in spacegroups if sg is not None)
    
    print(f"  ✅ CIFs extracted: {updated:,}")
    print(f"  ❌ Failed extractions: {failed:,}")
    if updated > 0:
        print(f"  ✅ Spacegroups parsed: {with_sg:,} ({100*with_sg/updated:.1f}% of extracted)")
    else:
        print(f"  ✅ Spacegroups parsed: {with_sg:,}")
    
    # Save updated index (keep original index structure)
    print(f"\n✅ Writing updated index to {args.out}...")
    df_merged.to_parquet(args.out, index=True)
    
    print(f"\n📊 Final statistics:")
    print(f"  Total records: {len(df_merged):,}")
    print(f"  With CIF files: {updated:,} ({100*updated/len(df_merged):.1f}%)")
    print(f"  With spacegroups: {with_sg:,} ({100*with_sg/len(df_merged):.1f}%)")


if __name__ == "__main__":
    main()
