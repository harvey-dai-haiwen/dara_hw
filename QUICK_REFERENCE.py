#!/usr/bin/env python
"""
Quick Reference: Using the Fixed Chemical System Filter

Run this script to see examples of the new filtering behavior.
"""

import sys
from pathlib import Path

repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root / 'scripts'))

print("=" * 70)
print("QUICK REFERENCE: Chemical System Filtering")
print("=" * 70)

print("""
✅ NEW DEFAULT BEHAVIOR (Chemical System Filter)
───────────────────────────────────────────────────────────────────

When you specify required_elements, you define a CHEMICAL SYSTEM.
The filter includes ALL possible subsystems:

Example: required_elements = ['Ge', 'Zn', 'O']

INCLUDES:
  ✅ Unary:   Ge, Zn, O
  ✅ Binary:  GeO, ZnO, GeZn (+ all stoichiometric variants)
  ✅ Ternary: GeZnO (+ all stoichiometric variants)

EXCLUDES:
  ❌ Anything with other elements (Fe, Cu, Al, Na, etc.)

This is CORRECT for XRD phase search because you want to find all
phases that could form from your starting materials!

CODE EXAMPLE:
─────────────
from scripts.dara_adapter import prepare_phases_for_dara

# Get all Ge-Zn-O subsystems from COD
phases = prepare_phases_for_dara(
    index_path='indexes/cod_index_filled.parquet',
    required_elements=['Ge', 'Zn', 'O'],  # Chemical system
    max_phases=500
)

# Result: Ge, Zn, O, GeO, ZnO, GeZn, GeZnO + variants
print(f"Found {len(phases)} phases")


═════════════════════════════════════════════════════════════════════

🔙 OLD BEHAVIOR (Exact Match - if needed)
───────────────────────────────────────────────────────────────────

If you specifically need phases containing ALL required elements:

Example: required_elements = ['Ge', 'Zn', 'O']

INCLUDES:
  ✅ Only phases with ALL three: GeZnO, Ge2Zn3O5, etc.

EXCLUDES:
  ❌ Ge, Zn, O (missing elements)
  ❌ GeO, ZnO, GeZn (missing elements)

CODE EXAMPLE:
─────────────
phases = prepare_phases_for_dara(
    index_path='indexes/cod_index_filled.parquet',
    required_elements=['Ge', 'Zn', 'O'],
    use_chemical_system=False,  # ← Disable new behavior
    max_phases=500
)

# Result: only GeZnO + quaternary compounds


═════════════════════════════════════════════════════════════════════

📋 COMMON USE CASES
───────────────────────────────────────────────────────────────────

1️⃣  Battery materials (Li-Co-O system):
   required_elements=['Li', 'Co', 'O']
   → Li, Co, O, LiO, CoO, LiCo, LiCoO2, etc.

2️⃣  Oxide ceramics (Ti-Al-O system):
   required_elements=['Ti', 'Al', 'O']
   → Ti, Al, O, TiO2, Al2O3, TiAl, TiAlO3, etc.

3️⃣  Exclude toxic elements:
   required_elements=['Fe', 'O']
   exclude_elements=['Pb', 'Hg', 'Cd']

4️⃣  Specific stoichiometry (old behavior):
   required_elements=['Fe', 'O']
   use_chemical_system=False
   → Only Fe2O3, FeO, Fe3O4, etc. (not pure Fe or O)


═════════════════════════════════════════════════════════════════════

🧪 TESTING YOUR FILTER
───────────────────────────────────────────────────────────────────

To verify what you'll get, run:

from scripts.database_interface import StructureDatabaseIndex

db = StructureDatabaseIndex('indexes/cod_index_filled.parquet')
filtered = db.filter_by_elements(allowed=['Your', 'Elements'])

print(f"Total phases: {len(filtered)}")
print(f"Compositions: {filtered['elements'].value_counts()}")

""")

print("=" * 70)
print("For full details, see: SETUP_AND_FIX_SUMMARY.md")
print("=" * 70)
