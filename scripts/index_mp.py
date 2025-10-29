#!/usr/bin/env python3
"""
Index Materials Project (MP) data: extract structures to CIF and build unified index.

This script processes MP pickle data to:
1. Extract Structure objects and export to CIF files
2. Classify experimental vs theoretical structures (based on database_IDs)
3. Extract crystallographic information (spacegroup, lattice params, etc.)
4. Generate parquet index in the same format as ICSD/COD

Usage:
    # Full indexing (single-thread, stable)
    python index_mp.py --input path/to/df_MP_*.pkl \
        --output mp_index.parquet \
        --cif-dir mp_cifs
    
    # Test with first 1000 records
    python index_mp.py --input path/to/df_MP_*.pkl \
        --output mp_index_test.parquet \
        --cif-dir mp_test_cifs \
        --sample 1000
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from tqdm import tqdm
import warnings

# Suppress pymatgen warnings
warnings.filterwarnings('ignore')


def classify_experimental_status(database_ids):
    """
    Classify experimental status based on database_IDs field.
    
    Args:
        database_ids: dict with database references (e.g., {'icsd': [...]})
        
    Returns:
        str: "experimental" if has any database ID, "theoretical" otherwise
    """
    if database_ids is None or pd.isna(database_ids):
        return "theoretical"
    
    if not isinstance(database_ids, dict):
        return "theoretical"
    
    # Check if dict has any non-empty values
    has_content = len(database_ids) > 0 and any(v for v in database_ids.values() if v)
    return "experimental" if has_content else "theoretical"


def extract_database_ids(database_ids):
    """
    Extract ICSD IDs from database_IDs field.
    
    Args:
        database_ids: dict like {'icsd': ['icsd-12345', ...]}
        
    Returns:
        list: ICSD ID numbers (empty list if none)
    """
    if not database_ids or not isinstance(database_ids, dict):
        return []
    
    icsd_ids = database_ids.get('icsd', [])
    if not icsd_ids:
        return []
    
    # Extract numeric IDs from strings like 'icsd-12345'
    numeric_ids = []
    for icsd_id in icsd_ids:
        if isinstance(icsd_id, str) and icsd_id.startswith('icsd-'):
            try:
                numeric_ids.append(int(icsd_id.replace('icsd-', '')))
            except ValueError:
                pass
    
    return numeric_ids


def extract_structure_info(structure):
    """
    Extract crystallographic information from pymatgen Structure.
    
    Args:
        structure: pymatgen Structure object
        
    Returns:
        dict: Lattice parameters and cell info
    """
    try:
        lattice = structure.lattice
        return {
            'a': lattice.a,
            'b': lattice.b,
            'c': lattice.c,
            'alpha': lattice.alpha,
            'beta': lattice.beta,
            'gamma': lattice.gamma,
            'cell_volume': structure.volume,
            'n_sites': len(structure),
            'density': structure.density,
        }
    except Exception as e:
        return {
            'a': None,
            'b': None,
            'c': None,
            'alpha': None,
            'beta': None,
            'gamma': None,
            'cell_volume': None,
            'n_sites': None,
            'density': None,
        }


def export_cif_safe(structure, output_path):
    """
    Safely export Structure to CIF file with error handling.
    
    Args:
        structure: pymatgen Structure object
        output_path: Path object for output CIF file
        
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    try:
        structure.to(filename=str(output_path), fmt="cif")
        return True, None
    except Exception as e:
        return False, str(e)


def process_mp_data(df_mp, cif_dir, sample_size=None):
    """
    Process MP dataframe and export CIFs.
    
    Args:
        df_mp: MP DataFrame
        cif_dir: Path to CIF output directory
        sample_size: Optional limit for testing
        
    Returns:
        DataFrame: Processed index with unified schema
    """
    # Sample if requested
    if sample_size and sample_size < len(df_mp):
        print(f"📋 Sampling first {sample_size:,} records...")
        df_mp = df_mp.head(sample_size)
    
    # Create CIF directory
    if cif_dir:
        cif_dir = Path(cif_dir)
        cif_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 CIF output directory: {cif_dir}")
    
    # Initialize result lists
    index_data = []
    
    print(f"\n🔧 Processing {len(df_mp):,} MP entries...")
    print("   Mode: Sequential processing (stable)")
    
    export_success = 0
    export_failed = 0
    
    for idx, row in tqdm(df_mp.iterrows(), total=len(df_mp), desc="Processing"):
        mp_id = row['material_id']
        
        # 1. Basic information
        record = {
            'source': 'MP',
            'raw_db_id': mp_id,
            'formula': row['formula_pretty'],
            'elements': row['elements'] if isinstance(row['elements'], list) else [],
            'nelements': row['nelements'],
        }
        
        # 2. Experimental status classification
        record['experimental_status'] = classify_experimental_status(row.get('database_IDs'))
        record['icsd_ids'] = extract_database_ids(row.get('database_IDs'))
        
        # 3. Symmetry information
        symmetry = row.get('symmetry', {})
        if isinstance(symmetry, dict):
            record['spacegroup'] = symmetry.get('symbol')
            record['crystal_system'] = symmetry.get('crystal_system')
        else:
            record['spacegroup'] = None
            record['crystal_system'] = None
        
        # 4. Extract structure info (lattice params, density, etc.)
        structure = row.get('structure')
        if structure is not None:
            struct_info = extract_structure_info(structure)
            record.update(struct_info)
        else:
            # Fill with None if no structure
            record.update({
                'a': None, 'b': None, 'c': None,
                'alpha': None, 'beta': None, 'gamma': None,
                'cell_volume': None, 'n_sites': None, 'density': None,
            })
        
        # 5. Energy information
        record['energy_above_hull'] = row.get('energy_above_hull')
        
        # 6. Export CIF
        cif_path_rel = None
        if cif_dir and structure is not None:
            # Create subdirectories like COD: mp/0/00/mp-1234.cif
            # Use first 3 chars of mp_id number for directory structure
            mp_num = mp_id.replace('mp-', '')
            if len(mp_num) >= 3:
                subdir1 = mp_num[0]
                subdir2 = mp_num[:2]
            else:
                subdir1 = '0'
                subdir2 = '00'
            
            cif_subdir = cif_dir / subdir1 / subdir2
            cif_subdir.mkdir(parents=True, exist_ok=True)
            
            cif_path = cif_subdir / f"{mp_id}.cif"
            success, error = export_cif_safe(structure, cif_path)
            
            if success:
                export_success += 1
                # Store relative path from workspace root
                cif_path_abs = cif_path.resolve()
                try:
                    cif_path_rel = str(cif_path_abs.relative_to(Path.cwd().resolve())).replace('\\', '/')
                except ValueError:
                    # If not relative, use absolute path
                    cif_path_rel = str(cif_path_abs).replace('\\', '/')
            else:
                export_failed += 1
                # Still keep the record but mark CIF as failed
                cif_path_rel = None
        
        record['path'] = cif_path_rel
        
        # 7. Extra metadata
        record['extra'] = {
            'formation_energy_per_atom': row.get('formation_energy_per_atom'),
            'band_gap': row.get('band_gap'),
        }
        
        index_data.append(record)
    
    # Print statistics
    print(f"\n📊 CIF Export Statistics:")
    if cif_dir:
        print(f"  ✅ Success: {export_success:,}")
        print(f"  ❌ Failed: {export_failed:,}")
        if export_success > 0:
            print(f"  📈 Success rate: {100*export_success/(export_success+export_failed):.1f}%")
    else:
        print(f"  ⚠️  CIF export skipped (no --cif-dir specified)")
    
    # Convert to DataFrame
    df_index = pd.DataFrame(index_data)
    
    # Classify experimental status summary
    exp_counts = df_index['experimental_status'].value_counts()
    print(f"\n📊 Experimental Status:")
    for status, count in exp_counts.items():
        print(f"  {status}: {count:,} ({100*count/len(df_index):.1f}%)")
    
    return df_index


def main():
    parser = argparse.ArgumentParser(description='Index Materials Project data')
    parser.add_argument('--input', required=True, help='Path to MP pickle file')
    parser.add_argument('--output', required=True, help='Output parquet file')
    parser.add_argument('--cif-dir', default='mp_cifs', help='Directory to export CIF files')
    parser.add_argument('--sample', type=int, default=None, help='Process only first N records (for testing)')
    parser.add_argument('--out-sqlite', type=Path, default=None, help='Optional: also export to SQLite')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Materials Project (MP) Indexing")
    print("=" * 70)
    
    # Check input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Error: Input file not found: {input_path}")
        return
    
    # Load MP data
    print(f"\n📖 Loading MP pickle from {input_path}...")
    try:
        df_mp = pd.read_pickle(input_path)
        print(f"   ✅ Loaded {len(df_mp):,} records")
    except Exception as e:
        print(f"❌ Error loading pickle: {e}")
        return
    
    # Process and export
    df_index = process_mp_data(df_mp, args.cif_dir, args.sample)
    
    # Save parquet
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\n� Writing index to {output_path}...")
    df_index.to_parquet(output_path, index=False)
    print(f"   ✅ Wrote {len(df_index):,} records")
    
    # Optional: SQLite
    if args.out_sqlite:
        print(f"\n💾 Writing SQLite to {args.out_sqlite}...")
        import sqlite3
        conn = sqlite3.connect(args.out_sqlite)
        df_index.to_sql('mp_index', conn, if_exists='replace', index=False)
        conn.close()
        print(f"   ✅ SQLite export complete")
    
    # Final statistics
    print(f"\n" + "=" * 70)
    print("✅ Indexing Complete!")
    print("=" * 70)
    print(f"\n📊 Final Statistics:")
    print(f"  Total entries: {len(df_index):,}")
    print(f"  With spacegroup: {df_index['spacegroup'].notna().sum():,} ({100*df_index['spacegroup'].notna().sum()/len(df_index):.1f}%)")
    print(f"  With CIF path: {df_index['path'].notna().sum():,} ({100*df_index['path'].notna().sum()/len(df_index):.1f}%)")
    print(f"  With energy_above_hull: {df_index['energy_above_hull'].notna().sum():,} ({100*df_index['energy_above_hull'].notna().sum()/len(df_index):.1f}%)")
    
    print(f"\n📁 Output files:")
    print(f"  Index: {output_path}")
    if args.cif_dir:
        print(f"  CIFs: {args.cif_dir}/")
    if args.out_sqlite:
        print(f"  SQLite: {args.out_sqlite}")


if __name__ == "__main__":
    main()
