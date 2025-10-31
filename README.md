# Dara v1.1.2hw — Streamlined XRD and Multi-Database Workflow

This README focuses on what’s new in 1.1.2hw and how to use Dara quickly. Advanced database rebuild (全量更新) instructions are at the end. For the legacy landing page, see `README_original.md`.

---

## ⭐ What’s new

- Unified multi-database workflow (ICSD, COD, MP) with one streamlined notebook
- MP integration with experimental/theoretical labels and stability filtering
- UV-based reproducible setup; helpers to build/verify indexes
- Original Dara functions fully retained, including XRD automatic search phase and refinement
- Rights reserved by original developers of Dara and databases

---

## 1) Quick Start (recommended path)

1. Environment setup (uv)

```powershell
git clone https://github.com/idocx/dara.git
cd dara

uv venv .venv --python 3.11
.\.venv\Scripts\Activate.ps1

uv pip install -e ".[docs]"
uv pip install jupyterlab ipykernel
python -m ipykernel install --user --name=dara-uv --display-name="Dara (uv)"
```

2. Place existing databases and indexes (do not add to Git)

```
dara/
├── cod_cifs/                  # COD CIF files (≈100 GB)
├── icsd_cifs/                 # ICSD CIF files (≈10 GB)
├── mp_cifs/                   # MP CIF files (~2 GB)
└── indexes/
    ├── cod_index_filled.parquet
    ├── icsd_index_filled.parquet
    ├── mp_index.parquet
    └── merged_index.parquet
```

Optional: link external data folders using symlinks on Windows PowerShell (Admin):

```powershell
New-Item -ItemType SymbolicLink -Path .\cod_cifs -Target "D:\\Data\\COD\\cifs"
New-Item -ItemType SymbolicLink -Path .\icsd_cifs -Target "D:\\Data\\ICSD\\cifs"
New-Item -ItemType SymbolicLink -Path .\mp_cifs   -Target "D:\\Data\\MP\\cifs"
```

3. Verify data presence

```powershell
python .\scripts\check_data_status.py
```

4. Run the streamlined notebook

```powershell
jupyter lab
```

Open `notebooks/streamlined_phase_analysis.ipynb`, select the "Dara (uv)" kernel, and run:
- Part 1: Pattern + environment configuration
- Part 2: Single-database phase search (COD/ICSD/MP/NONE) + exports
- Part 3: BGMN refinement + exports

Reports are saved under `~/Documents/dara_analysis/<ChemicalSystem>/reports/`.

More environment details and troubleshooting: `docs/environment_setup.md`.

---

---

## 🔧 Useful utilities

- `scripts/dara_adapter.py` – prepare CIF path lists for DARA `additional_phases`
- `scripts/database_interface.py` – unified filters across ICSD/COD/MP
- `scripts/list_xrd_elements.py` – regenerate `dataset/xrd_elements.csv`
- Helpers:
    - `scripts/setup_databases.ps1` – one-shot database setup (Windows PowerShell)
    - `scripts/check_data_status.py` – sanity check for indexes and CIF folders

---

## 🛡 Keep large data out of Git

We ignore CIF folders and indexes by default via `.gitignore`:

```
cod_cifs/
icsd_cifs/
mp_cifs/
indexes/
*.cif
```

If some were accidentally tracked, run (keep local files):

```powershell
git rm -r --cached cod_cifs icsd_cifs mp_cifs indexes
git commit -m "chore: untrack large datasets; keep files locally"
```

---

## 🧠 Advanced: Rebuild databases (全量更新)

All scripts live in `scripts/`. Summary commands for Windows PowerShell are shown; see `docs/database_update.md` for full instructions and validation steps.

### ICSD index
```powershell
# 1) Build raw index
python scripts/index_icsd.py \
    --csv "D:\\Data\\ICSD\\[Kedar_Group_ONLY]_ICSD2024_summary_2024.2_v5.3.0.csv" \
    --out indexes/icsd_index.parquet

# 2) Extract CIFs + fill spacegroups
python scripts/extract_icsd_cifs.py \
    --csv "D:\\Data\\ICSD\\[Kedar_Group_ONLY]_ICSD2024_summary_2024.2_v5.3.0.csv" \
    --index indexes/icsd_index.parquet \
    --cif-dir icsd_cifs \
    --out indexes/icsd_index_filled.parquet
```

### COD index
```powershell
# 1) Extract COD archive
tar -xJf D:\\Data\\COD\\cod-cifs-mysql.txz -C cod_cifs

# 2) Build parallel index
python scripts/index_cod_parallel.py \
    --cif-dir cod_cifs \
    --out indexes/cod_index.parquet \
    --workers 16

# 3) Fill spacegroups (sequential for stability)
python scripts/fill_spacegroup_cod.py \
    --index indexes/cod_index.parquet \
    --cif-dir cod_cifs \
    --out indexes/cod_index_filled.parquet \
    --workers 1
```

### Materials Project (MP) index
```powershell
python scripts/index_mp.py \
    --input "D:\\Data\\MP\\df_MP_20250211.pkl" \
    --output indexes/mp_index.parquet \
    --cif-dir mp_cifs
```

### Merge indices
```powershell
python scripts/merge_indices.py \
    --parquets indexes/icsd_index_filled.parquet indexes/cod_index_filled.parquet indexes/mp_index.parquet \
    --out-parquet indexes/merged_index.parquet \
    --out-json indexes/merged_index.json.gz \
    --out-sqlite indexes/merged_index.sqlite
```

Validate with: `scripts/verify_indices.py`, `verify_mp_index.py`, and `verify_merged.py`.

Full docs: `docs/database_update.md` and `docs/environment_setup.md`.
