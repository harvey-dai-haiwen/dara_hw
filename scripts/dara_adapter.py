#!/usr/bin/env python
"""
DARA adapter - external interface to use structure database indices with DARA.

This module provides helper functions to prepare filtered phases for DARA's
PhaseSearchMaker without modifying DARA's core code.
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pandas as pd
from database_interface import StructureDatabaseIndex


def prepare_phases_for_dara(
    index_path: str | Path,
    required_elements: list[str] | None = None,
    optional_elements: list[str] | None = None,
    exclude_elements: list[str] | None = None,
    formula_pattern: str | None = None,
    density_range: tuple[float, float] | None = None,
    sources: list[str] | None = None,
    experimental_only: bool = False,
    include_theoretical: bool = False,
    max_e_above_hull: float | None = None,
    max_phases: int | None = None,
    use_chemical_system: bool = True,
) -> list[str]:
    """
    Filter database index and return CIF paths for DARA PhaseSearchMaker.
    
    Args:
        index_path: Path to .parquet/.sqlite/.json.gz index file
        required_elements: Elements defining the chemical system (Ge-Zn-O).
                          When use_chemical_system=True (default), this includes all
                          subsystems: unary (Ge, Zn, O), binary (GeZn, ZnO, GeO), 
                          ternary (GeZnO), etc. Phases with other elements are excluded.
                          When use_chemical_system=False, phases must contain ALL
                          these elements (old exact-match behavior).
        optional_elements: (Only when use_chemical_system=False) May contain ANY of these
        exclude_elements: Must NOT contain any of these (applied after other filters)
        formula_pattern: Formula substring to match (case-insensitive)
        density_range: (min, max) density range in g/cm³
        sources: Filter by source ('ICSD', 'COD', 'MP')
        experimental_only: Include only experimental structures (MP only, default False)
        include_theoretical: Include theoretical structures (MP only, default False)
        max_e_above_hull: Max energy above hull in eV/atom (MP only, for stability filter)
        max_phases: Maximum number of phases to return
        use_chemical_system: If True (default), required_elements defines a chemical system
                            and includes all subsystems (Ge, Zn, O → Ge, Zn, O, GeZn, ZnO, GeO, GeZnO).
                            If False, uses old exact-match behavior (must contain ALL required_elements).
    
    Returns:
        List of CIF file paths
    
    Example:
        >>> from scripts.dara_adapter import prepare_phases_for_dara
        >>> from dara.jobs import PhaseSearchMaker
        >>> 
        >>> # Chemical system approach (NEW DEFAULT): Get all Ge-Zn-O subsystems
        >>> # Includes: Ge, Zn, O, GeZn, ZnO, GeO, GeZnO (excludes anything with other elements)
        >>> phases = prepare_phases_for_dara(
        ...     'indexes/cod_index_filled.parquet',
        ...     required_elements=['Ge', 'Zn', 'O'],
        ...     max_phases=500
        ... )
        >>> 
        >>> # Old exact-match behavior: must contain ALL required elements
        >>> phases = prepare_phases_for_dara(
        ...     'indexes/cod_index_filled.parquet',
        ...     required_elements=['Fe', 'O'],
        ...     exclude_elements=['Pb'],
        ...     use_chemical_system=False,
        ...     max_phases=500
        ... )
    """
    db = StructureDatabaseIndex(index_path)
    
    # Apply filters
    filtered = db.df
    
    # Element filtering: chemical system (new default) vs exact match (old behavior)
    if use_chemical_system and required_elements:
        # Chemical system filter: include all subsystems
        filtered = db.filter_by_elements(allowed=required_elements)
    elif required_elements or optional_elements:
        # Old exact-match behavior
        filtered = db.filter_by_elements(
            required=required_elements,
            optional=optional_elements,
            exclude=None  # Apply exclude separately below
        )
    
    # Apply exclude filter (always applied, regardless of mode)
    if exclude_elements:
        filtered = db.filter_by_elements(exclude=exclude_elements)
    
    if formula_pattern:
        filtered = db.filter_by_formula(formula_pattern)
    
    if density_range:
        min_d, max_d = density_range
        filtered = db.filter_by_density(min_val=min_d, max_val=max_d)
    
    if sources:
        filtered = db.filter_by_source(sources)
    
    # Filter by experimental status (MP only)
    if experimental_only:
        filtered = filtered[filtered['experimental_status'] == 'experimental'] if 'experimental_status' in filtered.columns else filtered
    elif include_theoretical:
        # Include both experimental and theoretical
        pass
    else:
        # Default: for MP data, include only experimental; for ICSD/COD, include all
        if 'experimental_status' in filtered.columns:
            filtered = filtered[filtered['experimental_status'] == 'experimental']
    
    # Filter by stability (MP only)
    if max_e_above_hull is not None and 'energy_above_hull' in filtered.columns:
        has_energy = filtered['energy_above_hull'].notna()
        stable = filtered[has_energy & (filtered['energy_above_hull'] <= max_e_above_hull)]
        # Keep non-MP data (no energy data)
        no_energy = filtered[~has_energy]
        filtered = pd.concat([stable, no_energy], ignore_index=True)
    
    # Get CIF paths
    if 'id' in filtered.columns:
        ids = filtered['id'].tolist()
    elif 'raw_db_id' in filtered.columns:
        ids = filtered['raw_db_id'].tolist()
    else:
        ids = None
    
    paths = db.get_cif_paths(ids)
    
    # Convert to absolute paths (critical for jobflow worker processes)
    # Worker processes may have different working directories
    repo_root = Path(__file__).parent.parent.resolve()
    absolute_paths = []
    for p in paths:
        if not p or p == 'None':
            continue
        path_obj = Path(p)
        if not path_obj.is_absolute():
            # Convert relative path to absolute using repo root
            path_obj = repo_root / path_obj
        if path_obj.exists():
            absolute_paths.append(str(path_obj))
    
    # Limit number of phases
    if max_phases and len(absolute_paths) > max_phases:
        absolute_paths = absolute_paths[:max_phases]
    
    return absolute_paths


def get_index_stats(index_path: str | Path) -> dict:
    """
    Get quick statistics about a database index.
    
    Args:
        index_path: Path to index file
    
    Returns:
        Dictionary with statistics
    
    Example:
        >>> stats = get_index_stats('indexes/merged_index.parquet')
        >>> print(f"Total phases: {stats['total_records']:,}")
        >>> print(f"Sources: {stats['sources']}")
    """
    db = StructureDatabaseIndex(index_path)
    return db.stats()


def export_filtered_phases(
    index_path: str | Path,
    output_path: str | Path,
    format: str = 'parquet',
    **filter_kwargs
) -> int:
    """
    Export filtered phases to a new index file.
    
    Args:
        index_path: Source index path
        output_path: Output file path
        format: Output format ('parquet', 'json.gz', 'csv')
        **filter_kwargs: Same as prepare_phases_for_dara
    
    Returns:
        Number of phases exported
    
    Example:
        >>> # Export all Fe-O phases to separate index
        >>> count = export_filtered_phases(
        ...     'indexes/merged_index.parquet',
        ...     'indexes/fe_o_phases.parquet',
        ...     required_elements=['Fe', 'O']
        ... )
        >>> print(f"Exported {count} Fe-O phases")
    """
    db = StructureDatabaseIndex(index_path)
    
    # Apply filters (reuse filter logic)
    filtered = db.df
    
    if filter_kwargs.get('required_elements') or filter_kwargs.get('optional_elements') or filter_kwargs.get('exclude_elements'):
        filtered = db.filter_by_elements(
            required=filter_kwargs.get('required_elements'),
            optional=filter_kwargs.get('optional_elements'),
            exclude=filter_kwargs.get('exclude_elements')
        )
    
    if filter_kwargs.get('formula_pattern'):
        filtered = db.filter_by_formula(filter_kwargs['formula_pattern'])
    
    if filter_kwargs.get('density_range'):
        min_d, max_d = filter_kwargs['density_range']
        filtered = db.filter_by_density(min_val=min_d, max_val=max_d)
    
    if filter_kwargs.get('sources'):
        filtered = db.filter_by_source(filter_kwargs['sources'])
    
    # Export
    db.export_filtered(filtered, output_path, format=format)
    
    return len(filtered)


def main():
    """CLI for quick testing."""
    import argparse
    
    p = argparse.ArgumentParser(description="DARA adapter - prepare phases for DARA")
    p.add_argument('index', help='Path to index file')
    p.add_argument('--elements-required', nargs='+', help='Required elements')
    p.add_argument('--elements-exclude', nargs='+', help='Excluded elements')
    p.add_argument('--source', nargs='+', choices=['ICSD', 'COD', 'MP'])
    p.add_argument('--max-phases', type=int, help='Maximum phases to return')
    p.add_argument('--stats', action='store_true', help='Show index statistics')
    
    args = p.parse_args()
    
    if args.stats:
        import json
        stats = get_index_stats(args.index)
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return
    
    paths = prepare_phases_for_dara(
        args.index,
        required_elements=args.elements_required,
        exclude_elements=args.elements_exclude,
        sources=args.source,
        max_phases=args.max_phases
    )
    
    print(f"✅ Found {len(paths)} CIF paths")
    print(f"\nFirst 10 paths:")
    for i, p in enumerate(paths[:10], 1):
        print(f"  {i}. {p}")
    
    if args.max_phases and len(paths) > args.max_phases:
        print(f"\n(Limited to {args.max_phases} phases as requested)")


if __name__ == '__main__':
    main()
