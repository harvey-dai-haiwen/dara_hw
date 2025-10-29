# Database Indexing & Query Scripts# Database Indexing & Query Scripts



This folder contains scripts for indexing and querying crystal structure databases (ICSD, COD, MP) to support DARA workflows.This folder contains scripts for indexing and querying crystal structure databases (ICSD, COD, MP) to support DARA workflows.



------



## 🗂️ Unified Database Interface## 🗂️ Unified Database Interface



All three databases (ICSD, COD, MP) now share a unified query interface and storage format.All three databases (ICSD, COD, MP) now share a unified query interface and storage format.



### Core Scripts### Core Scripts



#### 1. **database_interface.py** — Unified Query Interface#### 1. **database_interface.py** — Unified Query Interface

Provides a single interface to query all indexed databases with consistent filters.Provides a single interface to query all indexed databases with consistent filters.



**Key Features:****Key Features:**

- Multi-format support: parquet, sqlite, json.gz- Multi-format support: parquet, sqlite, json.gz

- Element-based filtering (required/optional/excluded)- Element-based filtering (required/optional)

- Formula, density, spacegroup filtering- Formula, density, spacegroup filtering

- **MP-specific**: Experimental/theoretical classification, thermodynamic stability filtering- CIF path extraction for DARA integration

- CIF path extraction for DARA integration- Export filtered results

- Export filtered results

**Usage Example:**

**Basic Usage:**```powershell

```python# Filter for Fe+O phases (e.g., Fe2O3, FeO)

from scripts.database_interface import StructureDatabaseIndexpython .\scripts\database_interface.py \

  --index .\indexes\merged_index.parquet \

# Load index  --elements-required Fe O \

db = StructureDatabaseIndex('indexes/merged_index.parquet')  --output filtered_fe_o.parquet



# Filter for Fe+O phases# Filter with density range

results = db.filter_by_elements(required=['Fe', 'O'])python .\scripts\database_interface.py \

print(f"Found {len(results)} Fe-O phases")  --index .\indexes\merged_index.parquet \

  --elements-required Li O \

# Filter by density range  --elements-optional Co Ni Mn \

results = db.filter_by_density(min_density=3.0, max_density=6.0, df=results)  --density-min 2.0 --density-max 6.0 \

  --output filtered_battery.parquet

# Export filtered results```

db.export_filtered(results, 'filtered_fe_o.parquet', include_paths=True)

```#### 2. **dara_adapter.py** — DARA External Adapter

Prepares filtered CIF paths for DARA's `additional_phases` without modifying DARA core code.

**MP-Specific Features:**

```python**Usage Example:**

# Load MP index```powershell

db_mp = StructureDatabaseIndex('indexes/mp_index.parquet')# Prepare phases for DARA

python .\scripts\dara_adapter.py \

# Filter for experimental structures only  --index .\indexes\merged_index.parquet \

experimental = db_mp.filter_by_experimental_status('experimental')  --elements-required Fe O \

  --max-phases 1000 \

# Filter for thermodynamically stable phases (E_hull ≤ 0.05 eV/atom)  --output fe_o_cif_paths.txt

stable = db_mp.filter_by_stability(max_e_above_hull=0.05)

# Use in DARA config

# Combine filters# additional_phases: fe_o_cif_paths.txt

li_co_o_stable = db_mp.filter_by_elements(required=['Li', 'Co', 'O'])```

li_co_o_stable = db_mp.filter_by_stability(max_e_above_hull=0.1, df=li_co_o_stable)

li_co_o_stable = db_mp.filter_by_experimental_status('experimental', df=li_co_o_stable)---

```

## 🏗️ Database Indexing Scripts

#### 2. **dara_adapter.py** — DARA External Adapter

Prepares filtered CIF paths for DARA's `additional_phases` without modifying DARA core code.Each database has dedicated indexing scripts for full-scale or incremental updates.



**Key Features:**### ICSD Indexing

- Automatic index loading and element filtering

- Max phases limit for DARA performance**Scripts:**

- **MP-specific**: Experimental-only mode, theoretical inclusion, stability thresholds- `index_icsd.py` — Build ICSD index from CSV (full rebuild)

- Direct CIF path list output- `extract_icsd_cifs.py` — Extract inline CIFs and fill spacegroups



**Basic Usage:****Data Source:** Kedar Group internal ICSD CSV (229,487 entries)

```python

from scripts.dara_adapter import prepare_phases_for_dara**Workflow:**

```powershell

# Prepare ICSD+COD phases for DARA# Step 1: Build initial index from CSV

cif_paths = prepare_phases_for_dara(python .\scripts\index_icsd.py \

    index_path='indexes/merged_index.parquet',  --csv "C:\path\to\[Kedar_Group_ONLY]_ICSD2024_summary_2024.2_v5.3.0.csv" \

    required_elements=['Li', 'Co', 'O'],  --out .\indexes\icsd_index.parquet

    max_phases=500

)# Step 2: Extract CIFs and fill spacegroups

```python .\scripts\extract_icsd_cifs.py \

  --csv "C:\path\to\[Kedar_Group_ONLY]_ICSD2024_summary_2024.2_v5.3.0.csv" \

**MP-Specific Usage:**  --index .\indexes\icsd_index.parquet \

```python  --cif-dir icsd_cifs \

# Experimental structures only (default for MP)  --out .\indexes\icsd_index_filled.parquet

cif_paths = prepare_phases_for_dara(```

    index_path='indexes/mp_index.parquet',

    required_elements=['Li', 'Mn', 'O'],**Output:**

    experimental_only=True- `icsd_index_filled.parquet`: 229,487 entries, 97.2% with spacegroups

)- `icsd_cifs/`: Extracted CIF files organized by CollectionCode



# Include thermodynamically stable theoretical phases---

cif_paths = prepare_phases_for_dara(

    index_path='indexes/mp_index.parquet',### COD Indexing

    required_elements=['Li', 'Mn', 'O'],

    include_theoretical=True,**Scripts:**

    max_e_above_hull=0.1  # eV/atom, stability threshold- `index_cod_parallel.py` — Build COD index from CIF directory (parallel)

)- `fill_spacegroup_cod.py` — Re-parse CIFs to fill missing spacegroups



# Use in DARA PhaseSearchMaker**Data Source:** COD tar.xz archive (521,901 CIFs)

from dara import PhaseSearchMaker

maker = PhaseSearchMaker(**Workflow:**

    required_elements=['Li', 'Mn', 'O'],```powershell

    additional_phases=cif_paths  # Use prepared MP phases# Step 1: Extract COD tar.xz

)tar -xJf cod-cifs-mysql.txz -C .\cod_cifs

```

# Step 2: Build initial index (parallel)

---python .\scripts\index_cod_parallel.py \

  --cif-dir .\cod_cifs \

## 🏗️ Database Indexing Scripts  --out .\indexes\cod_index.parquet \

  --workers 16

Each database has dedicated indexing scripts for full-scale rebuilds.

# Step 3: Fill missing spacegroups (sequential for stability)

### ICSD Indexingpython .\scripts\fill_spacegroup_cod.py \

  --index .\indexes\cod_index.parquet \

**Scripts:**  --cif-dir . \

- `index_icsd.py` — Build ICSD index from CSV  --out .\indexes\cod_index_filled.parquet \

- `extract_icsd_cifs.py` — Extract inline CIFs and fill spacegroups  --workers 1

```

**Data Source:** Kedar Group internal ICSD CSV (229,487 entries)

**Output:**

**Workflow:**- `cod_index_filled.parquet`: 501,975 entries, 98.5% with spacegroups

```bash- Processing time: ~14 hours (single-thread, stable)

# Step 1: Build initial index from CSV

python scripts/index_icsd.py \---

  --csv "path/to/ICSD2024_summary.csv" \

  --out indexes/icsd_index.parquet### MP Indexing



# Step 2: Extract CIFs and fill spacegroups**Scripts:**

python scripts/extract_icsd_cifs.py \- `index_mp.py` — **PLACEHOLDER** for Materials Project indexing

  --csv "path/to/ICSD2024_summary.csv" \

  --index indexes/icsd_index.parquet \**Data Source:** MP pickle file (169,385 entries)

  --cif-dir icsd_cifs \

  --out indexes/icsd_index_filled.parquet**Current Status:**

```- ⚠️ Placeholder script created

- 📋 Schema defined (matching ICSD/COD)

**Output:**- ⏳ Implementation pending

- `icsd_index_filled.parquet`: 229,487 entries, 97.2% with spacegroups

- `icsd_cifs/`: Extracted CIF files organized by CollectionCode**Future Workflow:**

- Processing time: ~2.18 hours```powershell

# Once implemented

---python .\scripts\index_mp.py \

  --input "C:\path\to\df_MP_20250211.pkl" \

### COD Indexing  --output .\indexes\mp_index.parquet \

  --cif-dir mp_cifs

**Scripts:**```

- `index_cod_parallel.py` — Build COD index from CIF directory (parallel)

- `fill_spacegroup_cod.py` — Re-parse CIFs to fill missing spacegroups---



**Data Source:** COD tar.xz archive (521,901 CIFs)## 🔗 Merge & Validate



**Workflow:**### Merge Indices

```bashCombine multiple database indices into a unified index.

# Step 1: Extract COD tar.xz

tar -xJf cod-cifs-mysql.txz -C cod_cifs```powershell

python .\scripts\merge_indices.py \

# Step 2: Build initial index (parallel for speed)  --parquets .\indexes\icsd_index_filled.parquet .\indexes\cod_index_filled.parquet \

python scripts/index_cod_parallel.py \  --out-parquet .\indexes\merged_index.parquet \

  --cif-dir cod_cifs \  --out-json .\indexes\merged_index.json.gz \

  --out indexes/cod_index.parquet \  --out-sqlite .\indexes\merged_index.sqlite

  --workers 16```



# Step 3: Fill missing spacegroups (single-thread for stability)**Current Merged Index:**

python scripts/fill_spacegroup_cod.py \- **Total**: 731,462 entries

  --index indexes/cod_index.parquet \- **ICSD**: 229,487 entries (97.2% with spacegroups)

  --cif-dir . \- **COD**: 501,975 entries (98.5% with spacegroups)

  --out indexes/cod_index_filled.parquet \- **Overall**: 98.1% spacegroup coverage, 100% CIF path coverage

  --workers 1

```### Verify Indices

Validate index integrity and format.

**Output:**

- `cod_index_filled.parquet`: 501,975 entries, 98.5% with spacegroups```powershell

- Processing time: ~13.88 hours (spacegroup filling)# Verify individual indices

python .\scripts\verify_indices.py .\indexes\icsd_index_filled.parquet

---python .\scripts\verify_indices.py .\indexes\cod_index_filled.parquet



### MP Indexing ✨ NEW# Verify merged index

python .\scripts\verify_merged.py .\indexes\merged_index.parquet

**Scripts:**

- `index_mp.py` — Build MP index from pickle, extract CIFs, classify experimental/theoretical# Generate quality report

- `verify_mp_index.py` — Validate MP index completeness and qualitypython .\scripts\generate_report.py .\indexes\merged_index.parquet

```

**Data Source:** Materials Project pickle file (169,385 entries)

---

**Workflow:**

```bash## 📊 Index Schema

# Generate complete MP index with CIF extraction

python scripts/index_mp.py \All indices follow a unified schema:

  --input "path/to/df_MP_20250211.pkl" \

  --output indexes/mp_index.parquet \| Column | Type | Description | Source |

  --cif-dir mp_cifs|--------|------|-------------|--------|

```| `source` | str | Database source (ICSD/COD/MP) | All |

| `raw_db_id` | str | Original database ID | All |

**Output:**| `formula` | str | Chemical formula | All |

- `mp_index.parquet`: 169,385 entries, 100% with spacegroups| `elements` | list[str] | Element symbols (e.g., ["Fe", "O"]) | All |

  * **Experimental**: 59,936 (35.4%) — identified via `database_IDs` field| `nelements` | int | Number of unique elements | All |

  * **Theoretical**: 109,449 (64.6%) — DFT-computed structures| `spacegroup` | str | Space group symbol (e.g., "Fm-3m") | All |

- `mp_cifs/`: Exported CIF files from pymatgen Structure objects| `density` | float | Calculated density (g/cm³) | All |

- Processing time: ~9 minutes| `cell_volume` | float | Unit cell volume (ų) | All |

| `n_sites` | int | Number of atomic sites | All |

**MP-Specific Features:**| `a`, `b`, `c` | float | Lattice parameters (Å) | ICSD/COD |

1. **Experimental/Theoretical Classification**: Automatic classification based on `database_IDs` field| `alpha`, `beta`, `gamma` | float | Lattice angles (°) | ICSD/COD |

2. **Thermodynamic Stability**: `energy_above_hull` (eV/atom) for stability filtering| `crystal_system` | str | Crystal system | ICSD/COD |

3. **Structure → CIF Conversion**: All structures exported to CIF format| `path` | str | Relative path to CIF file | All |

4. **100% Coverage**: Spacegroup, CIF path, and energy data completeness| `extra` | dict | Additional metadata | All |



**Quality Metrics:**---

- Spacegroup coverage: 100% (169,385/169,385)

- CIF export success: 100% (169,385/169,385)## 🛠️ Legacy Scripts

- Energy data coverage: 100% (all entries have `energy_above_hull`)

The following scripts are retained for reference but superseded by the unified interface:

---

- `build_candidate_index.py` — Original multi-source index builder

## 🔗 Merge & Validate- `filter_icsd.py` — ICSD-specific filtering

- `filter_cod.py` — COD-specific filtering

### Merge Indices- `run_binary_reaction.py` — Binary reaction dataset indexing

Combine ICSD and COD indices into a unified index (MP kept separate due to experimental/theoretical distinction).- `run_precursor_mixture.py` — Precursor mixture dataset indexing



```bash---

python scripts/merge_indices.py \

  --parquets indexes/icsd_index_filled.parquet indexes/cod_index_filled.parquet \## 💡 Tips & Best Practices

  --out-parquet indexes/merged_index.parquet \

  --out-json indexes/merged_index.json.gz \### Performance Optimization

  --out-sqlite indexes/merged_index.sqlite- **Parallel Processing**: Use `--workers N` for initial indexing (be mindful of RAM/disk I/O)

```- **Sequential Mode**: Use `--workers 1` for spacegroup filling (more stable for large datasets)

- **Incremental Updates**: Run full indexing only when database updates; use cached indices for queries

**Current Index Statistics:**

### Memory Management

| Index | Entries | Spacegroup Coverage | CIF Coverage | Experimental | Theoretical |- **Large Datasets**: COD/MP indexing may require 32GB+ RAM with many workers

|-------|---------|---------------------|--------------|--------------|-------------|- **Disk I/O**: SSDs recommended for CIF parsing; expect 100+ GB for extracted COD

| **ICSD** | 229,487 | 97.2% | 100% | 100% | 0% |

| **COD** | 501,975 | 98.5% | 100% | 100% | 0% |### Integration with DARA

| **merged (ICSD+COD)** | 731,462 | 98.1% | 100% | 100% | 0% |1. Use `database_interface.py` to filter phases

| **MP** | 169,385 | 100% | 100% | 35.4% | 64.6% |2. Use `dara_adapter.py` to prepare CIF paths

| **Total** | 900,847 | 98.6% | 100% | 79.1% | 20.9% |3. Add paths to DARA config `additional_phases`

4. Run DARA workflows as usual

### Verify Indices

Validate index integrity and format.---



```bash## 📝 Data Files

# Verify individual indices

python scripts/verify_indices.py indexes/icsd_index_filled.parquet**Included:**

python scripts/verify_indices.py indexes/cod_index_filled.parquet- `mp_struct_info.json.gz` — MP formula/spacegroup/e_hull lookup (for legacy scripts)



# Verify MP index (includes experimental/theoretical stats)**Generated:**

python scripts/verify_mp_index.py indexes/mp_index.parquet- `indexes/icsd_index_filled.parquet` — ICSD index with CIFs

- `indexes/cod_index_filled.parquet` — COD index with spacegroups

# Verify merged index- `indexes/merged_index.parquet` — Unified ICSD+COD index

python scripts/verify_merged.py indexes/merged_index.parquet- `icsd_cifs/` — Extracted ICSD CIF files (~10 GB)

- `cod_cifs/` — Extracted COD CIF files (~102 GB)

# Generate quality report

python scripts/generate_report.py indexes/merged_index.parquet---

```

## 🔧 Development Notes

---

### Design Principles

## 📊 Index Schema- **No Core Modification**: External adapters (e.g., `dara_adapter.py`) instead of modifying DARA source

- **Full Rebuild Mode**: Each indexing run regenerates indices (no incremental logic)

All indices follow a unified schema:- **Unified Schema**: All databases use identical column names/types for seamless merging



| Column | Type | Description | ICSD | COD | MP |### Future Improvements

|--------|------|-------------|------|-----|-----|- [ ] Implement MP indexing (extract from pickle → parquet + CIFs)

| `source` | str | Database source (ICSD/COD/MP) | ✅ | ✅ | ✅ |- [ ] Add incremental update mode (track database versions)

| `raw_db_id` | str | Original database ID | ✅ | ✅ | ✅ |- [ ] Integrate quality metrics (duplicate detection, anomaly flagging)

| `formula` | str | Chemical formula | ✅ | ✅ | ✅ |- [ ] Optimize memory usage for COD parallel indexing

| `elements` | list[str] | Element symbols (e.g., ["Fe", "O"]) | ✅ | ✅ | ✅ |

| `nelements` | int | Number of unique elements | ✅ | ✅ | ✅ |---

| `spacegroup` | str | Space group symbol (e.g., "Fm-3m") | ✅ | ✅ | ✅ |

| `density` | float | Calculated density (g/cm³) | ✅ | ✅ | ✅ |## 📞 Support

| `cell_volume` | float | Unit cell volume (ų) | ✅ | ✅ | ✅ |

| `n_sites` | int | Number of atomic sites | ✅ | ✅ | ✅ |For questions or issues:

| `path` | str | Relative path to CIF file | ✅ | ✅ | ✅ |1. Check this README

| `experimental_status` | str | 'experimental' or 'theoretical' | ❌ | ❌ | ✅ |2. Review script docstrings (`python script.py --help`)

| `energy_above_hull` | float | Thermodynamic stability (eV/atom) | ❌ | ❌ | ✅ |3. Contact: Kedar Group (internal)

| `extra` | dict | Additional metadata | ✅ | ✅ | ✅ |

---

**MP-Specific Columns:**

- `experimental_status`: Classification based on `database_IDs` (non-empty = experimental)**Last Updated:** October 29, 2025  

- `energy_above_hull`: 0.0 = stable phase, > 0.0 = metastable (higher = less stable)**Version:** 2.0 (Unified Interface)


---

## 💡 Common Workflows

### 1. Query Experimental Fe-O Phases
```python
from scripts.database_interface import StructureDatabaseIndex

# Use merged index (ICSD+COD, all experimental)
db = StructureDatabaseIndex('indexes/merged_index.parquet')
results = db.filter_by_elements(required=['Fe', 'O'])
print(f"Found {len(results)} experimental Fe-O phases")

# Use MP index (experimental only)
db_mp = StructureDatabaseIndex('indexes/mp_index.parquet')
mp_exp = db_mp.filter_by_experimental_status('experimental')
mp_fe_o = db_mp.filter_by_elements(required=['Fe', 'O'], df=mp_exp)
print(f"Found {len(mp_fe_o)} MP experimental Fe-O phases")
```

### 2. Find Stable Li-Mn-O Phases for Battery Research
```python
from scripts.dara_adapter import prepare_phases_for_dara

# Get stable experimental + theoretical phases (E_hull ≤ 0.1 eV/atom)
cif_paths = prepare_phases_for_dara(
    index_path='indexes/mp_index.parquet',
    required_elements=['Li', 'Mn', 'O'],
    include_theoretical=True,
    max_e_above_hull=0.1,  # Only stable/metastable phases
    max_phases=500
)

print(f"Prepared {len(cif_paths)} stable Li-Mn-O phases for DARA")
```

### 3. Cross-Database Validation (TiO2 Example)
```python
from scripts.database_interface import StructureDatabaseIndex

# Query ICSD+COD
db_icsd_cod = StructureDatabaseIndex('indexes/merged_index.parquet')
tio2_exp = db_icsd_cod.filter_by_formula('TiO2')

# Query MP experimental
db_mp = StructureDatabaseIndex('indexes/mp_index.parquet')
mp_tio2 = db_mp.filter_by_formula('TiO2')
mp_tio2_exp = db_mp.filter_by_experimental_status('experimental', df=mp_tio2)

# Query MP theoretical
mp_tio2_theo = db_mp.filter_by_experimental_status('theoretical', df=mp_tio2)

print(f"ICSD+COD: {len(tio2_exp)} TiO2 structures (all experimental)")
print(f"MP: {len(mp_tio2_exp)} experimental + {len(mp_tio2_theo)} theoretical")
```

### 4. Get Index Statistics
```python
from scripts.dara_adapter import get_index_stats

# ICSD+COD stats
stats_icsd_cod = get_index_stats('indexes/merged_index.parquet')
print(stats_icsd_cod)
# Output:
# {
#   'total_records': 731462,
#   'sources': {'COD': 501975, 'ICSD': 229487},
#   'spacegroup_coverage': 0.981,
#   'path_coverage': 1.0
# }

# MP stats
stats_mp = get_index_stats('indexes/mp_index.parquet')
print(stats_mp)
# Output:
# {
#   'total_records': 169385,
#   'sources': {'MP': 169385},
#   'experimental': 59936,
#   'theoretical': 109449,
#   'spacegroup_coverage': 1.0,
#   'path_coverage': 1.0
# }
```

---

## 🧪 Testing

### Run All Tests
```bash
# Run pytest suite (29 tests)
pytest scripts/test_pytest_suite.py -v
```

**Test Coverage:**
- ✅ Basic queries (element, formula, density, spacegroup)
- ✅ MP features (experimental/theoretical, stability filtering)
- ✅ ICSD/COD behavior (all experimental, no theoretical)
- ✅ DARA adapter integration
- ✅ Edge cases (empty queries, boundary values)
- ✅ Data integrity (coverage, consistency)

---

## 🛠️ Legacy Scripts

The following scripts are retained for reference:

- `build_candidate_index.py` — Original multi-source index builder
- `filter_icsd.py` — ICSD-specific filtering (use `database_interface.py` instead)
- `filter_cod.py` — COD-specific filtering (use `database_interface.py` instead)
- `run_binary_reaction.py` — Binary reaction dataset indexing
- `run_precursor_mixture.py` — Precursor mixture dataset indexing

---

## 💡 Tips & Best Practices

### Choosing the Right Index

| Use Case | Recommended Index | Reason |
|----------|-------------------|--------|
| Known materials (experimental only) | `merged_index.parquet` | ICSD+COD, all experimental, 731k entries |
| New materials discovery | `mp_index.parquet` (theoretical) | DFT-computed structures, 109k entries |
| Cross-validation | Both indices | Experimental (merged) + theoretical (MP) |
| Battery materials | `mp_index.parquet` (stable) | Filter by `energy_above_hull` ≤ 0.1 |

### Performance Optimization

- **Index Loading**: < 1 second for all indices
- **Simple Queries**: < 2 seconds (e.g., element filtering)
- **Complex Queries**: < 3 seconds (multi-filter, large result sets)
- **Parallel Indexing**: Use `--workers N` for initial builds (RAM-intensive)
- **Sequential Mode**: Use `--workers 1` for spacegroup filling (more stable)

### Memory Management

- **ICSD Indexing**: ~4 GB RAM
- **COD Indexing**: ~16 GB RAM (parallel), ~8 GB (sequential)
- **MP Indexing**: ~8 GB RAM
- **Query Operations**: < 2 GB RAM

### Integration with DARA

```python
# Example: Prepare phases for DARA PhaseSearchMaker
from scripts.dara_adapter import prepare_phases_for_dara
from dara import PhaseSearchMaker

# Get stable Li-Mn-O phases from MP
cif_paths = prepare_phases_for_dara(
    index_path='indexes/mp_index.parquet',
    required_elements=['Li', 'Mn', 'O'],
    include_theoretical=True,
    max_e_above_hull=0.05,  # Very stable phases only
    max_phases=500
)

# Use in DARA
maker = PhaseSearchMaker(
    required_elements=['Li', 'Mn', 'O'],
    additional_phases=cif_paths
)
```

---

## 📝 Data Files

**Included:**
- `mp_struct_info.json.gz` — MP formula/spacegroup/e_hull lookup (legacy)

**Generated:**
- `indexes/icsd_index_filled.parquet` — 229,487 ICSD entries
- `indexes/cod_index_filled.parquet` — 501,975 COD entries
- `indexes/merged_index.parquet` — 731,462 ICSD+COD entries
- `indexes/mp_index.parquet` — 169,385 MP entries ✨ NEW
- `icsd_cifs/` — Extracted ICSD CIF files (~10 GB)
- `cod_cifs/` — Extracted COD CIF files (~102 GB)
- `mp_cifs/` — Generated MP CIF files (~2 GB) ✨ NEW

---

## 🔧 Development Notes

### Design Principles

1. **Unified Interface**: All databases share identical query API
2. **No Core Modification**: External adapters (e.g., `dara_adapter.py`) instead of modifying DARA
3. **Full Rebuild Mode**: Each indexing run regenerates indices (no incremental logic)
4. **MP-Specific Features**: Experimental/theoretical classification, stability filtering
5. **100% Quality**: All indices have complete spacegroup and CIF path coverage

### Architecture

```
Database Sources
├── ICSD CSV → index_icsd.py → icsd_index_filled.parquet (229k, 97.2% spacegroup)
├── COD tar.xz → index_cod_parallel.py → cod_index_filled.parquet (502k, 98.5% spacegroup)
└── MP pickle → index_mp.py → mp_index.parquet (169k, 100% spacegroup)
                                              ↓
                                    Unified Query Interface
                                    (database_interface.py)
                                              ↓
                                      DARA Adapter
                                    (dara_adapter.py)
                                              ↓
                                    DARA PhaseSearchMaker
```

---

## 🚀 Quick Start

### 1. Query Existing Indices
```python
from scripts.database_interface import StructureDatabaseIndex

# Load and query
db = StructureDatabaseIndex('indexes/merged_index.parquet')
results = db.filter_by_elements(required=['Li', 'Co', 'O'])
print(f"Found {len(results)} Li-Co-O phases")
```

### 2. Prepare Phases for DARA
```python
from scripts.dara_adapter import prepare_phases_for_dara

cif_paths = prepare_phases_for_dara(
    index_path='indexes/mp_index.parquet',
    required_elements=['Li', 'Mn', 'O'],
    max_phases=500
)
```

### 3. Run Tests
```bash
pytest scripts/test_pytest_suite.py -v
```

---

## 📞 Support

For questions or issues:
1. Check this README
2. Review script docstrings (`python script.py --help`)
3. Run tests: `pytest scripts/test_pytest_suite.py -v`
4. Contact: Kedar Group (internal)

---

**Last Updated:** October 29, 2025  
**Version:** 3.0 (MP Integration Complete)
