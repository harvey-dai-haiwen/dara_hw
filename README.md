![DARA logo](docs/_static/logo-with-text.svg)

# Dara 3.0 — Streamlined XRD and Multi-Database Workflow

This release-centered README explains how to set up the environment, configure the three databases (ICSD, COD, MP), build compatible indexes, and run the streamlined phase analysis notebook.

If you want the legacy landing page, see `README_original.md`.

---

## 1) Environment setup (uv recommended)

```powershell
git clone https://github.com/idocx/dara.git
cd dara

uv venv .venv --python 3.11
.\.venv\Scripts\Activate.ps1

uv pip install -e ".[docs]"
uv pip install jupyterlab ipykernel
python -m ipykernel install --user --name=dara-uv --display-name="Dara (uv)"
```

Details and troubleshooting: `docs/environment_setup.md`.

---

## 2) Database layout (not in Git)

Place data outside Git (these folders are `.gitignore`d):

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

We do not commit these to GitHub. See `.gitignore` and the section below on how to build them.

---

## 3) Build compatible indexes (全量更新)

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

---

## 4) Run the streamlined notebook

```powershell
jupyter lab
```

Open `notebooks/streamlined_phase_analysis.ipynb`, select the "Dara (uv)" kernel, and run cells sequentially:

- Part 1: Pattern + environment configuration
- Part 2: Single-database phase search (COD/ICSD/MP/NONE) + exports
- Part 3: BGMN refinement + exports

Reports are saved under `~/Documents/dara_analysis/<ChemicalSystem>/reports/`.

---

## 5) Keep large data out of Git

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

## 6) Useful utilities

- `scripts/dara_adapter.py` – prepare CIF path lists for DARA `additional_phases`
- `scripts/database_interface.py` – unified filters across ICSD/COD/MP
- `scripts/list_xrd_elements.py` – regenerate `dataset/xrd_elements.csv`

Full docs: `docs/database_update.md`, `docs/environment_setup.md`, and `RELEASE_v3.0.md`.
