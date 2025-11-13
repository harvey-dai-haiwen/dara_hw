# Dara v1.1.2hw — Streamlined XRD and Multi-Database Workflow# Dara v1.1.2hw — Streamlined XRD and Multi-Database Workflow



**Version**: 1.1.2+hw_v0.2  This README focuses on what’s new in 1.1.2hw and how to use Dara quickly. Advanced database rebuild (全量更新) instructions are at the end. For the legacy landing page, see `README_original.md`.

**Python**: ≥3.10 (tested on 3.10-3.13)  

**Package Manager**: UV (recommended)---



---## ⭐ What’s new



## ⭐ What's New- Unified multi-database workflow (ICSD, COD, MP) with one streamlined notebook

- MP integration with experimental/theoretical labels and stability filtering

- **Unified multi-database workflow** (ICSD, COD, MP) with streamlined notebook- UV-based reproducible setup; helpers to build/verify indexes

- **Materials Project integration** with experimental/theoretical classification and stability filtering  - Original Dara functions fully retained, including XRD automatic search phase and refinement

- **UV-based reproducible environment** - one command setup with all dependencies- Rights reserved by original developers of Dara and databases

- **Chemical system filtering** - automatically includes all subsystems (unary, binary, ternary)

- **Dependency verification** - built-in script to validate installation---

- Original Dara functions fully retained, including XRD automatic search phase and refinement

## 🌐 Web Portals

### Original Dara Web Portal (Port 8898)

- Launch the upstream FastAPI + Gatsby UI with the built-in CLI:

```powershell
uv run python -m dara.cli server --host 127.0.0.1 --port 8898
```

- Open a browser at `http://localhost:8898` to use the legacy reaction-predictor workflow.
- Submit jobs with `POST /api/submit` (see `docs/web_server.md` for API details). Poll status via `GET /api/task/{wf_id}` or browse queued jobs at `/tasks` in the UI.
- Optional: export `MP_API_KEY=<your-key>` before starting to enable Materials Project reaction prediction.

### Dara Local Multi-Database Portal (Port 8899)

- Launch the extended local copy (COD / ICSD / MP selector) with:

```powershell
uv run python launch_local_server.py
```

- The server boots on `http://localhost:8899` and automatically spawns its queue worker.
- Submit searches with `POST /api/search` and poll results with `GET /api/task/{wf_id}`. Each request is queued, so the API returns immediately with a workflow ID.
- Use `example_api_usage_async.py` for a ready-to-run polling client, or inspect `JOB_QUEUE_INTEGRATION.md` for the async workflow and job-queue architecture.
- Custom CIF uploads and chemical-system filtering are supported; CIFs are cleaned up automatically after job completion.

---

## 1) Quick Start (recommended path)

---

1. Environment setup (uv)

## 🚀 Quick Start

```powershell

### 1. Install UV Package Managergit clone https://github.com/idocx/dara.git

cd dara

**Windows (PowerShell)**:

```powershelluv venv .venv --python 3.11

powershell -c "irm https://astral.sh/uv/install.ps1 | iex".\.venv\Scripts\Activate.ps1

```

uv pip install -e ".[docs]"

**macOS/Linux**:uv pip install jupyterlab ipykernel

```bashpython -m ipykernel install --user --name=dara-uv --display-name="Dara (uv)"

curl -LsSf https://astral.sh/uv/install.sh | sh```

```

2. Place existing databases and indexes (do not add to Git)

### 2. Setup Environment

```

```bashdara/

# Clone repository├── cod_cifs/                  # COD CIF files (≈100 GB)

git clone https://github.com/harvey-dai-haiwen/dara_hw.git├── icsd_cifs/                 # ICSD CIF files (≈10 GB)

cd dara├── mp_cifs/                   # MP CIF files (~2 GB)

└── indexes/

# Install all dependencies (one command!)    ├── cod_index_filled.parquet

uv sync    ├── icsd_index_filled.parquet

    ├── mp_index.parquet

# Verify installation (optional)    └── merged_index.parquet

uv run python verify_dependencies.py```

```

Optional: link external data folders using symlinks on Windows PowerShell (Admin):

**Expected output**:

``````powershell

✅ All critical dependencies are available! (27/27 packages OK)New-Item -ItemType SymbolicLink -Path .\cod_cifs -Target "D:\\Data\\COD\\cifs"

```New-Item -ItemType SymbolicLink -Path .\icsd_cifs -Target "D:\\Data\\ICSD\\cifs"

New-Item -ItemType SymbolicLink -Path .\mp_cifs   -Target "D:\\Data\\MP\\cifs"

### 3. Place Database Files```



Place your database CIF files and indices (not tracked by Git):3. Verify data presence



``````powershell

dara/python .\scripts\check_data_status.py

├── cod_cifs/                  # COD CIF files (≈100 GB)```

├── icsd_cifs/                 # ICSD CIF files (≈10 GB)

├── mp_cifs/                   # MP CIF files (~2 GB)4. Run the streamlined notebook

└── indexes/

    ├── cod_index_filled.parquet```powershell

    ├── icsd_index_filled.parquetjupyter lab

    ├── mp_index.parquet```

    └── merged_index.parquet

```Open `notebooks/streamlined_phase_analysis.ipynb`, select the "Dara (uv)" kernel, and run:

- Part 1: Pattern + environment configuration

**Optional**: Link external data folders using symlinks:- Part 2: Single-database phase search (COD/ICSD/MP/NONE) + exports

- Part 3: BGMN refinement + exports

**Windows (PowerShell Admin)**:

```powershellReports are saved under `~/Documents/dara_analysis/<ChemicalSystem>/reports/`.

New-Item -ItemType SymbolicLink -Path .\cod_cifs -Target "D:\Data\COD\cifs"

New-Item -ItemType SymbolicLink -Path .\icsd_cifs -Target "D:\Data\ICSD\cifs"More environment details and troubleshooting: `docs/environment_setup.md`.

New-Item -ItemType SymbolicLink -Path .\mp_cifs -Target "D:\Data\MP\cifs"

```---



**Linux/macOS**:---

```bash

ln -s /path/to/COD/cifs cod_cifs## 🔧 Useful utilities

ln -s /path/to/ICSD/cifs icsd_cifs

ln -s /path/to/MP/cifs mp_cifs- `scripts/dara_adapter.py` – prepare CIF path lists for DARA `additional_phases`

```- `scripts/database_interface.py` – unified filters across ICSD/COD/MP

- `scripts/list_xrd_elements.py` – regenerate `dataset/xrd_elements.csv`

### 4. Verify Data Status- Helpers:

    - `scripts/setup_databases.ps1` – one-shot database setup (Windows PowerShell)

```bash    - `scripts/check_data_status.py` – sanity check for indexes and CIF folders

uv run python scripts/check_data_status.py

```---



### 5. Run Analysis## 🛡 Keep large data out of Git



Start Jupyter and open the streamlined notebook:We ignore CIF folders and indexes by default via `.gitignore`:



```bash```

uv run jupyter labcod_cifs/

```icsd_cifs/

mp_cifs/

Open `notebooks/streamlined_phase_analysis.ipynb` and run:indexes/

- **Part 1**: XRD pattern and setup*.cif

- **Part 2**: Database selection + Phase search + Visualization```

- **Part 3**: Advanced refinement with custom parameters

If some were accidentally tracked, run (keep local files):

Reports are automatically saved to `~/Documents/dara_analysis/<ChemicalSystem>/reports/`.

```powershell

---git rm -r --cached cod_cifs icsd_cifs mp_cifs indexes

git commit -m "chore: untrack large datasets; keep files locally"

## 📖 Documentation```



- **UV Setup Guide**: `UV_SETUP_GUIDE.md` - Detailed environment setup and troubleshooting---

- **Environment Setup**: `docs/environment_setup.md` - Python environment configuration

- **Database Update**: `docs/database_update.md` - Full database rebuild instructions## 🧠 Advanced: Rebuild databases (全量更新)

- **Tutorials**: `docs/tutorials.md` - Example workflows

- **CHANGELOG**: `CHANGELOG.md` - Version history and changesAll scripts live in `scripts/`. Summary commands for Windows PowerShell are shown; see `docs/database_update.md` for full instructions and validation steps.



---### ICSD index

```powershell

## 🔧 Useful Utilities# 1) Build raw index

python scripts/index_icsd.py \

Located in `scripts/`:    --csv "D:\\Data\\ICSD\\[Kedar_Group_ONLY]_ICSD2024_summary_2024.2_v5.3.0.csv" \

    --out indexes/icsd_index.parquet

- **`dara_adapter.py`** – Prepare filtered CIF lists for DARA phase search

- **`database_interface.py`** – Unified filtering across ICSD/COD/MP databases# 2) Extract CIFs + fill spacegroups

- **`check_data_status.py`** – Verify database indices and CIF folderspython scripts/extract_icsd_cifs.py \

- **`verify_dependencies.py`** – Validate Python environment    --csv "D:\\Data\\ICSD\\[Kedar_Group_ONLY]_ICSD2024_summary_2024.2_v5.3.0.csv" \

- **`list_xrd_elements.py`** – Regenerate `dataset/xrd_elements.csv`    --index indexes/icsd_index.parquet \

    --cif-dir icsd_cifs \

**Windows PowerShell Helper**:    --out indexes/icsd_index_filled.parquet

- **`setup_databases.ps1`** – One-shot database setup script```



---### COD index

```powershell

## 🛡️ Data Management# 1) Extract COD archive

tar -xJf D:\\Data\\COD\\cod-cifs-mysql.txz -C cod_cifs

### .gitignore Configuration

# 2) Build parallel index

Large data files are excluded from Git by default:python scripts/index_cod_parallel.py \

    --cif-dir cod_cifs \

```gitignore    --out indexes/cod_index.parquet \

cod_cifs/    --workers 16

icsd_cifs/

mp_cifs/# 3) Fill spacegroups (sequential for stability)

indexes/python scripts/fill_spacegroup_cod.py \

*.cif    --index indexes/cod_index.parquet \

```    --cif-dir cod_cifs \

    --out indexes/cod_index_filled.parquet \

### Remove Accidentally Tracked Files    --workers 1

```

If database files were accidentally committed:

### Materials Project (MP) index

```bash```powershell

# Remove from Git but keep local filespython scripts/index_mp.py \

git rm -r --cached cod_cifs icsd_cifs mp_cifs indexes    --input "D:\\Data\\MP\\df_MP_20250211.pkl" \

git commit -m "chore: untrack large datasets; keep files locally"    --output indexes/mp_index.parquet \

```    --cif-dir mp_cifs

```

---

### Merge indices

## 🔬 Advanced: Database Rebuild```powershell

python scripts/merge_indices.py \

Full database indexing instructions are available in `docs/database_update.md`.    --parquets indexes/icsd_index_filled.parquet indexes/cod_index_filled.parquet indexes/mp_index.parquet \

    --out-parquet indexes/merged_index.parquet \

### Quick Reference    --out-json indexes/merged_index.json.gz \

    --out-sqlite indexes/merged_index.sqlite

**ICSD**:```

```bash

# Build index and extract CIFsValidate with: `scripts/verify_indices.py`, `verify_mp_index.py`, and `verify_merged.py`.

uv run python scripts/index_icsd.py --csv <ICSD_CSV> --out indexes/icsd_index.parquet

uv run python scripts/extract_icsd_cifs.py --index indexes/icsd_index.parquet --cif-dir icsd_cifsFull docs: `docs/database_update.md` and `docs/environment_setup.md`.

```

**COD**:
```bash
# Extract archive and build index
tar -xJf cod-cifs-mysql.txz -C cod_cifs
uv run python scripts/index_cod_parallel.py --cif-dir cod_cifs --out indexes/cod_index.parquet
uv run python scripts/fill_spacegroup_cod.py --index indexes/cod_index.parquet --out indexes/cod_index_filled.parquet
```

**Materials Project**:
```bash
uv run python scripts/index_mp.py --input <MP_PKL> --output indexes/mp_index.parquet --cif-dir mp_cifs
```

**Merge Indices**:
```bash
uv run python scripts/merge_indices.py \
    --parquets indexes/icsd_index_filled.parquet indexes/cod_index_filled.parquet indexes/mp_index.parquet \
    --out-parquet indexes/merged_index.parquet
```

---

## 📦 Alternative Installation (pip)

If you prefer traditional pip installation:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .\.venv\Scripts\Activate.ps1  # Windows

pip install -e ".[docs]"
pip install jupyterlab ipykernel
```

---

## 📄 License

MIT License - See `LICENSE` file for details.

Original Dara developed by Yuxing Fei and Matthew McDermott.  
This fork (dara_hw) maintained by Harvey Dai.

---

## 🙏 Acknowledgments

- Original Dara developers: Yuxing Fei, Matthew McDermott
- Database sources: ICSD, COD, Materials Project
- BGMN Rietveld refinement engine

---

For detailed documentation, see:
- **Quick Start**: This README
- **Full Setup**: `UV_SETUP_GUIDE.md`
- **Database Management**: `docs/database_update.md`
- **Troubleshooting**: `docs/environment_setup.md`
