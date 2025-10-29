#!/usr/bin/env python
"""
Fill missing spacegroup information in COD index by re-parsing CIF files.

This script:
1. Reads existing COD index (parquet)
2. Re-parses CIF files to extract spacegroup using pymatgen
3. Updates index with spacegroup information
4. Outputs updated parquet index

Uses parallel processing for performance.
"""
from __future__ import annotations

import argparse
import json
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from tqdm import tqdm

warnings.filterwarnings('ignore')


def parse_cif_spacegroup(cif_path: str) -> tuple[str, str | None]:
    """
    Parse CIF file to extract spacegroup.
    
    Args:
        cif_path: Path to CIF file
    
    Returns:
        (cif_path, spacegroup_symbol) or (cif_path, None) if failed
    """
    try:
        from pymatgen.core import Structure
        
        if not Path(cif_path).exists():
            return (cif_path, None)
        
        struct = Structure.from_file(cif_path)
        
        # Get space group analyzer
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
        sga = SpacegroupAnalyzer(struct)
        sg_symbol = sga.get_space_group_symbol()
        
        return (cif_path, sg_symbol)
    
    except Exception as e:
        # Return None for failed parsing
        return (cif_path, None)


def main():
    p = argparse.ArgumentParser(description="Fill COD spacegroup by re-parsing CIF files")
    p.add_argument('--index', type=Path, required=True, help='Input COD index (.parquet)')
    p.add_argument('--cif-dir', type=Path, required=True, help='Directory containing COD CIF files')
    p.add_argument('--out', type=Path, required=True, help='Output index (.parquet)')
    p.add_argument('--workers', type=int, default=12, help='Number of parallel workers')
    p.add_argument('--sample', type=int, help='Process only first N records (for testing)')
    
    args = p.parse_args()
    
    print(f"📖 Loading COD index from {args.index}...")
    df = pd.read_parquet(args.index, engine='pyarrow')
    print(f"  Total records: {len(df):,}")
    
    # Filter records that need spacegroup (currently None or NaN)
    needs_sg = df['spacegroup'].isna() | (df['spacegroup'] == 'None')
    print(f"  Records needing spacegroup: {needs_sg.sum():,}")
    
    # Also filter records that have valid paths
    has_path = df['path'].notna() & (df['path'] != 'None')
    to_process = needs_sg & has_path
    print(f"  Records with valid paths to process: {to_process.sum():,}")
    
    if to_process.sum() == 0:
        print("✅ No records to process (all have spacegroup or no path)")
        return
    
    # Get list of CIF paths to process
    cif_paths = df.loc[to_process, 'path'].tolist()
    
    # Convert relative paths to absolute if needed
    cif_paths_abs = []
    for p in cif_paths:
        if not Path(p).is_absolute():
            # Try relative to cif_dir
            abs_p = args.cif_dir / p
            if abs_p.exists():
                cif_paths_abs.append(str(abs_p))
            else:
                cif_paths_abs.append(p)  # Keep original if not found
        else:
            cif_paths_abs.append(p)
    
    if args.sample:
        print(f"⚠️  Sampling first {args.sample} records for testing")
        cif_paths_abs = cif_paths_abs[:args.sample]
        to_process_indices = df[to_process].index[:args.sample]
    else:
        to_process_indices = df[to_process].index
    
    print(f"\n🔧 Parsing {len(cif_paths_abs):,} CIF files...")
    print(f"   Workers: {args.workers} (use --workers 1 for sequential processing)")
    print("   This may take a while depending on file count...")
    
    # Process (parallel or sequential based on workers)
    results = {}
    
    if args.workers == 1:
        # Sequential processing - lower memory/disk pressure
        print("   Using sequential processing (lower memory usage)")
        for path in tqdm(cif_paths_abs, desc="Parsing CIFs"):
            _, sg = parse_cif_spacegroup(path)
            results[path] = sg
    else:
        # Parallel processing
        print(f"   Using parallel processing with {args.workers} workers")
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(parse_cif_spacegroup, path): path for path in cif_paths_abs}
            
            with tqdm(total=len(futures), desc="Parsing CIFs") as pbar:
                for future in as_completed(futures):
                    path, sg = future.result()
                    results[path] = sg
                    pbar.update(1)
    
    # Update dataframe
    print("\n📝 Updating index with spacegroup information...")
    updated_count = 0
    failed_count = 0
    
    for idx, path in zip(to_process_indices, cif_paths_abs):
        sg = results.get(path)
        if sg:
            df.at[idx, 'spacegroup'] = sg
            updated_count += 1
        else:
            failed_count += 1
    
    print(f"  ✅ Updated: {updated_count:,}")
    print(f"  ❌ Failed/Not found: {failed_count:,}")
    
    # Write output
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, index=False)
    print(f"\n✅ Wrote updated index to {args.out}")
    
    # Summary stats
    final_has_sg = df['spacegroup'].notna() & (df['spacegroup'] != 'None')
    print(f"\n📊 Final statistics:")
    print(f"  Total records: {len(df):,}")
    print(f"  With spacegroup: {final_has_sg.sum():,} ({final_has_sg.sum()/len(df)*100:.1f}%)")
    print(f"  Without spacegroup: {(~final_has_sg).sum():,}")


if __name__ == '__main__':
    main()
