# Database Full-Refresh Guide

This document explains how to rebuild the ICSD, COD, and Materials Project (MP) databases that ship with Dara 3.0. The focus is on **full refreshes** (全量更新) from raw data exports to the indexed formats consumed by Dara and the streamlined phase analysis notebook.

---

## 1. Directory layout

The repository expects the following structure once all databases are processed:

```
dara/
├── cod_cifs/                  # COD CIF files (≈100 GB)
├── icsd_cifs/                 # ICSD CIF files (≈10 GB)
├── mp_cifs/                   # MP CIF files exported from Structures (≈2 GB)
└── indexes/
    ├── cod_index_filled.parquet
    ├── icsd_index_filled.parquet
    ├── mp_index.parquet
    └── merged_index.parquet
```

All indexing scripts live in `scripts/`. Example commands below assume you are in the repository root with an activated environment (see `docs/environment_setup.md`).

---

## 2. ICSD full rebuild

### 2.1 Source data

- **Input:** `[Kedar_Group_ONLY]_ICSD2024_summary_2024.2_v5.3.0.csv`
- **Location hint:** Internal Kedar Group shared drive `Materials_DB/ICSD/exports/2024/`
- **Contents:** One row per ICSD entry with inline CIF and metadata columns.

### 2.2 Steps

```powershell
# 1. Build the raw index (Parquet)
python scripts/index_icsd.py \
  --csv "D:\Data\ICSD\[Kedar_Group_ONLY]_ICSD2024_summary_2024.2_v5.3.0.csv" \
  --out indexes/icsd_index.parquet

# 2. Extract embedded CIFs + fill missing space groups
python scripts/extract_icsd_cifs.py \
  --csv "D:\Data\ICSD\[Kedar_Group_ONLY]_ICSD2024_summary_2024.2_v5.3.0.csv" \
  --index indexes/icsd_index.parquet \
  --cif-dir icsd_cifs \
  --out indexes/icsd_index_filled.parquet

# 3. Validate the result
python scripts/verify_indices.py indexes/icsd_index_filled.parquet
```

**Expected outcome**
- `icsd_cifs/` populated with subdirectories per Collection Code
- `indexes/icsd_index_filled.parquet` (~8 MB) with ~229k rows and >97% space group coverage

---

## 3. COD full rebuild

### 3.1 Source data

- **Input:** `cod-cifs-mysql.txz` archive from Crystallography Open Database
- **Location hint:** Internal mirror `Materials_DB/COD/2025-08/`
- **Contents:** 500k+ CIF files packaged in a tar.xz archive

### 3.2 Steps

```powershell
# 1. Extract the archive (takes several hours on HDD)
tar -xJf D:\Data\COD\cod-cifs-mysql.txz -C cod_cifs

# 2. Build initial parallel index (uses multiprocessing)
python scripts/index_cod_parallel.py \
  --cif-dir cod_cifs \
  --out indexes/cod_index.parquet \
  --workers 16

# 3. Re-parse CIFs sequentially to fill missing space groups
python scripts/fill_spacegroup_cod.py \
  --index indexes/cod_index.parquet \
  --cif-dir cod_cifs \
  --out indexes/cod_index_filled.parquet \
  --workers 1

# 4. Validate
python scripts/verify_indices.py indexes/cod_index_filled.parquet
```

**Expected outcome**
- `cod_cifs/` mirrors COD directory layout (~100 GB)
- `indexes/cod_index_filled.parquet` (~35 MB) with ~502k rows and >98% space group coverage

---

## 4. Materials Project full rebuild

### 4.1 Source data

- **Input:** `df_MP_20250211.pkl` (Pandas DataFrame exported via Materials Project internal tooling)
- **Location hint:** Internal archive `Materials_DB/MP/full_exports/2025-02-11/`
- **Contents:** `Structure` objects with metadata, `energy_above_hull`, `database_IDs`, etc.

### 4.2 Steps

```powershell
# 1. Build MP index and export CIFs
python scripts/index_mp.py \
  --input "D:\Data\MP\df_MP_20250211.pkl" \
  --output indexes/mp_index.parquet \
  --cif-dir mp_cifs

# 2. Validate MP-specific fields
python scripts/verify_mp_index.py indexes/mp_index.parquet
```

**Expected outcome**
- `mp_cifs/` with one CIF per MP entry (~2 GB)
- `indexes/mp_index.parquet` (~19 MB) with 169k rows, classified as experimental vs theoretical

---

## 5. Merge the databases

Once each individual index is refreshed, merge them into the unified parquet used by Dara utilities.

```powershell
python scripts/merge_indices.py \
  --parquets indexes/icsd_index_filled.parquet indexes/cod_index_filled.parquet indexes/mp_index.parquet \
  --out-parquet indexes/merged_index.parquet \
  --out-json indexes/merged_index.json.gz \
  --out-sqlite indexes/merged_index.sqlite

# Optional: run integrity checks
python scripts/verify_merged.py indexes/merged_index.parquet
python scripts/generate_report.py indexes/merged_index.parquet
```

**Expected outcome**
- `merged_index.parquet` (~42 MB) with ~900k entries
- Matching JSON and SQLite exports for external tooling

---

## 6. Post-refresh housekeeping

1. Update dataset metadata:
   ```powershell
   python scripts/list_xrd_elements.py --dataset-root dataset --output dataset/xrd_elements.csv
   ```
2. Commit the refreshed indexes and CIF manifests to internal storage (the full CIF directories are too large for Git).
3. Re-run `notebooks/streamlined_phase_analysis.ipynb` against the updated indexes to confirm phase search succeeds for a known benchmark (e.g., GeO₂-ZnO dataset).
4. Publish SHA256 checksums of the new parquet files to the private Confluence page for reproducibility.

---

## 7. Reference

- `scripts/index_icsd.py` — Parse ICSD CSV with inline CIFs
- `scripts/index_cod_parallel.py` — Build COD index using multiprocessing
- `scripts/index_mp.py` — Convert MP pickle into parquet + CIFs
- `scripts/dara_adapter.py` — Filter merged index into phase lists for DARA
- `docs/environment_setup.md` — Environment instructions for running the scripts

---

**Last updated:** October 30, 2025
