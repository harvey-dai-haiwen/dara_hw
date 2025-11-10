#!/usr/bin/env python
"""
Unified interface for querying structure database indices.

Supports ICSD, COD, MP and merged indices in parquet/sqlite/json.gz formats.
"""
from __future__ import annotations

import json
import gzip
from pathlib import Path
from typing import Any, Literal

import pandas as pd


class StructureDatabaseIndex:
    """Unified structure database index interface."""
    
    def __init__(self, index_path: str | Path):
        """
        Initialize from index file.
        
        Args:
            index_path: Path to .parquet, .sqlite, or .json.gz index file
        """
        self.index_path = Path(index_path)
        if not self.index_path.exists():
            raise FileNotFoundError(f"Index file not found: {self.index_path}")
        
        self.df = self._load_index()
        self._validate_schema()
    
    def _load_index(self) -> pd.DataFrame:
        """Load index from file."""
        suffix = self.index_path.suffix.lower()
        
        if suffix == '.parquet':
            return pd.read_parquet(self.index_path, engine='pyarrow')
        
        elif suffix == '.sqlite':
            import sqlite3
            conn = sqlite3.connect(str(self.index_path))
            # Try common table names
            for table in ['index', 'cod_index', 'icsd_index', 'mp_index']:
                try:
                    df = pd.read_sql(f"SELECT * FROM {table}", conn)
                    conn.close()
                    # Deserialize JSON columns
                    for col in ['elements', 'extra']:
                        if col in df.columns:
                            df[col] = df[col].apply(
                                lambda x: json.loads(x) if isinstance(x, str) and x.startswith('[') else x
                            )
                    return df
                except:
                    continue
            conn.close()
            raise ValueError(f"No valid table found in {self.index_path}")
        
        elif suffix == '.gz':
            with gzip.open(self.index_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
            return pd.DataFrame(data)
        
        else:
            raise ValueError(f"Unsupported format: {suffix}. Use .parquet, .sqlite, or .json.gz")
    
    def _validate_schema(self):
        """Validate required columns exist."""
        required = ['source', 'formula', 'elements']
        missing = [col for col in required if col not in self.df.columns]
        if missing:
            raise ValueError(f"Index missing required columns: {missing}")
    
    def filter_by_elements(
        self,
        required: list[str] | None = None,
        optional: list[str] | None = None,
        exclude: list[str] | None = None,
        allowed: list[str] | None = None
    ) -> pd.DataFrame:
        """
        Filter by element composition.
        
        Args:
            required: Must contain ALL these elements (exact requirement)
            optional: May contain ANY of these (in addition to required)
            exclude: Must NOT contain any of these
            allowed: ALL phase elements must be subset of this list (chemical system filter)
                    This is for filtering by chemical system: e.g., allowed=['Ge','Zn','O']
                    will include Ge, Zn, O, GeZn, ZnO, GeO, GeZnO but exclude anything
                    containing other elements. Mutually exclusive with required/optional.
        
        Returns:
            Filtered DataFrame
        
        Example:
            >>> db = StructureDatabaseIndex('indexes/merged_index.parquet')
            >>> # Exact requirement: must contain both Fe AND O
            >>> fe_o = db.filter_by_elements(required=['Fe', 'O'], exclude=['Pb'])
            >>> 
            >>> # Chemical system: include all subsystems (Ge, Zn, O, GeZn, ZnO, GeO, GeZnO)
            >>> ge_zn_o_system = db.filter_by_elements(allowed=['Ge', 'Zn', 'O'])
        """
        df = self.df.copy()
        
        # Ensure elements column is list type (handle numpy arrays from parquet)
        if 'elements' in df.columns:
            import numpy as np
            df['elements'] = df['elements'].apply(
                lambda x: list(x) if isinstance(x, (list, np.ndarray)) and x is not None else (
                    json.loads(x) if isinstance(x, str) and x.startswith('[') else []
                )
            )
        
        # Chemical system filter: all phase elements must be subset of allowed
        if allowed:
            allowed_set = set(allowed)
            df = df[df['elements'].apply(
                lambda x: set(x).issubset(allowed_set) if isinstance(x, list) and len(x) > 0 else False
            )]
        else:
            # Original behavior
            if required:
                df = df[df['elements'].apply(lambda x: all(e in x for e in required) if isinstance(x, list) else False)]
            
            if optional:
                # Must contain at least one optional element (in addition to required)
                df = df[df['elements'].apply(lambda x: any(e in x for e in optional) if isinstance(x, list) else False)]
        
        if exclude:
            df = df[df['elements'].apply(lambda x: not any(e in x for e in exclude) if isinstance(x, list) else True)]
        
        return df
    
    def filter_by_formula(self, pattern: str, case_sensitive: bool = False) -> pd.DataFrame:
        """
        Filter by chemical formula pattern (substring match).
        
        Args:
            pattern: Formula pattern to match (e.g., 'Fe2O3', 'NaCl')
            case_sensitive: Whether to match case-sensitively
        
        Returns:
            Filtered DataFrame
        """
        df = self.df.copy()
        if 'formula' not in df.columns:
            return df
        
        formula_col = df['formula'].fillna('')
        if not case_sensitive:
            return df[formula_col.str.lower().str.contains(pattern.lower(), na=False)]
        else:
            return df[formula_col.str.contains(pattern, na=False)]
    
    def filter_by_density(self, min_val: float | None = None, max_val: float | None = None) -> pd.DataFrame:
        """
        Filter by density range.
        
        Args:
            min_val: Minimum density (g/cm³)
            max_val: Maximum density (g/cm³)
        
        Returns:
            Filtered DataFrame
        """
        df = self.df.copy()
        if 'density' not in df.columns:
            return df
        
        if min_val is not None:
            df = df[df['density'] >= min_val]
        if max_val is not None:
            df = df[df['density'] <= max_val]
        
        return df
    
    def filter_by_spacegroup(self, spacegroups: list[str | int]) -> pd.DataFrame:
        """
        Filter by space group.
        
        Args:
            spacegroups: List of space group symbols or numbers
        
        Returns:
            Filtered DataFrame
        """
        df = self.df.copy()
        if 'spacegroup' not in df.columns:
            return df
        
        # Convert all to strings for comparison
        sg_strs = [str(sg) for sg in spacegroups]
        return df[df['spacegroup'].astype(str).isin(sg_strs)]
    
    def filter_by_source(self, sources: list[str]) -> pd.DataFrame:
        """
        Filter by database source.
        
        Args:
            sources: List of sources ('ICSD', 'COD', 'MP')
        
        Returns:
            Filtered DataFrame
        """
        return self.df[self.df['source'].isin(sources)]
    
    def filter_by_experimental_status(
        self, 
        status: Literal['experimental', 'theoretical', 'all'] = 'all'
    ) -> pd.DataFrame:
        """
        Filter by experimental status (MP only).
        
        For ICSD/COD data, all records are considered experimental.
        For MP data, uses the 'experimental_status' field.
        
        Args:
            status: 'experimental', 'theoretical', or 'all'
        
        Returns:
            Filtered DataFrame
        
        Examples:
            >>> db = StructureDatabaseIndex('mp_index.parquet')
            >>> exp_only = db.filter_by_experimental_status('experimental')
            >>> print(f"Experimental structures: {len(exp_only)}")
        """
        if status == 'all':
            return self.df
        
        # For MP data, filter by experimental_status
        if 'experimental_status' in self.df.columns:
            filtered = self.df[self.df['experimental_status'] == status].copy()
        else:
            # ICSD/COD are all experimental
            if status == 'experimental':
                filtered = self.df.copy()
            else:
                filtered = pd.DataFrame(columns=self.df.columns)
        
        return filtered
    
    def filter_by_stability(self, max_e_above_hull: float = 0.1) -> pd.DataFrame:
        """
        Filter by thermodynamic stability (MP only).
        
        Filters structures based on energy_above_hull field.
        ICSD/COD data (without this field) are passed through unchanged.
        
        Args:
            max_e_above_hull: Maximum energy above hull (eV/atom)
        
        Returns:
            Filtered DataFrame
        
        Examples:
            >>> db = StructureDatabaseIndex('mp_index.parquet')
            >>> stable = db.filter_by_stability(max_e_above_hull=0.05)
            >>> print(f"Stable structures: {len(stable)}")
        """
        if 'energy_above_hull' not in self.df.columns:
            # No stability data, return all
            return self.df
        
        # Filter rows with energy data
        has_energy = self.df['energy_above_hull'].notna()
        no_energy = ~has_energy
        
        # Apply filter to rows with energy data
        stable = self.df[has_energy & (self.df['energy_above_hull'] <= max_e_above_hull)]
        
        # Keep rows without energy data (ICSD/COD)
        no_energy_rows = self.df[no_energy]
        
        # Combine
        filtered = pd.concat([stable, no_energy_rows], ignore_index=True)
        
        return filtered
    
    def get_cif_paths(self, ids: list[str | int] | None = None) -> list[str]:
        """
        Get CIF file paths for given IDs.
        
        Args:
            ids: List of record IDs. If None, returns all paths.
        
        Returns:
            List of CIF file paths (absolute or relative)
        """
        if ids is None:
            df = self.df
        else:
            # Try to match by 'id', 'raw_db_id', or index
            if 'id' in self.df.columns:
                df = self.df[self.df['id'].isin(ids)]
            elif 'raw_db_id' in self.df.columns:
                df = self.df[self.df['raw_db_id'].isin(ids)]
            else:
                df = self.df.iloc[ids]
        
        if 'path' not in df.columns:
            return []
        
        paths = df['path'].dropna().tolist()
        return [str(p) for p in paths]
    
    def export_filtered(
        self,
        filtered_df: pd.DataFrame,
        output_path: str | Path,
        format: Literal['parquet', 'json.gz', 'csv'] = 'parquet'
    ):
        """
        Export filtered results to file.
        
        Args:
            filtered_df: DataFrame to export (from filter_* methods)
            output_path: Output file path
            format: Output format ('parquet', 'json.gz', 'csv')
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'parquet':
            filtered_df.to_parquet(output_path, index=False)
        elif format == 'json.gz':
            records = filtered_df.to_dict(orient='records')
            with gzip.open(output_path, 'wt', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        elif format == 'csv':
            # Serialize list columns to JSON strings for CSV
            df_csv = filtered_df.copy()
            for col in df_csv.columns:
                if df_csv[col].apply(lambda x: isinstance(x, (list, dict))).any():
                    df_csv[col] = df_csv[col].apply(
                        lambda x: json.dumps(x) if isinstance(x, (list, dict)) else x
                    )
            df_csv.to_csv(output_path, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def stats(self) -> dict[str, Any]:
        """
        Get index statistics.
        
        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_records': len(self.df),
            'sources': self.df['source'].value_counts().to_dict() if 'source' in self.df.columns else {},
            'columns': list(self.df.columns),
        }
        
        # Completeness
        completeness = {}
        for col in ['formula', 'elements', 'path', 'spacegroup', 'density']:
            if col in self.df.columns:
                non_null = self.df[col].notna().sum()
                completeness[col] = {
                    'count': int(non_null),
                    'percentage': round(non_null / len(self.df) * 100, 1)
                }
        stats['completeness'] = completeness
        
        return stats
    
    def __repr__(self) -> str:
        stats = self.stats()
        return (
            f"StructureDatabaseIndex('{self.index_path.name}')\n"
            f"  Records: {stats['total_records']:,}\n"
            f"  Sources: {stats['sources']}\n"
            f"  Columns: {len(stats['columns'])}"
        )


def main():
    """CLI for quick testing."""
    import argparse
    
    p = argparse.ArgumentParser(description="Query structure database index")
    p.add_argument('index', help='Path to index file (.parquet/.sqlite/.json.gz)')
    p.add_argument('--elements-required', nargs='+', help='Required elements')
    p.add_argument('--elements-exclude', nargs='+', help='Excluded elements')
    p.add_argument('--formula', help='Formula pattern')
    p.add_argument('--source', nargs='+', choices=['ICSD', 'COD', 'MP'], help='Filter by source')
    p.add_argument('--stats', action='store_true', help='Show statistics')
    p.add_argument('--export', help='Export filtered results to this path')
    p.add_argument('--export-format', choices=['parquet', 'json.gz', 'csv'], default='parquet')
    
    args = p.parse_args()
    
    db = StructureDatabaseIndex(args.index)
    
    if args.stats:
        import json
        print(json.dumps(db.stats(), indent=2, ensure_ascii=False))
        return
    
    # Apply filters
    df = db.df
    
    if args.elements_required or args.elements_exclude:
        df = db.filter_by_elements(
            required=args.elements_required,
            exclude=args.elements_exclude
        )
    
    if args.formula:
        df = db.filter_by_formula(args.formula)
    
    if args.source:
        df = db.filter_by_source(args.source)
    
    print(f"Filtered results: {len(df):,} records")
    
    if len(df) > 0:
        print(f"\nFirst 5 rows:")
        key_cols = [c for c in ['source', 'formula', 'elements', 'spacegroup', 'path'] if c in df.columns]
        print(df[key_cols].head(5).to_string(index=False))
    
    if args.export:
        db.export_filtered(df, args.export, format=args.export_format)
        print(f"\n✅ Exported to {args.export}")


if __name__ == '__main__':
    main()
