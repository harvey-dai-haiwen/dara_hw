# Dara v1.1.2hw_v0.3 — XRD Phase Analysis with Multi-Database Support# Dara v1.1.2hw — Streamlined XRD and Multi-Database Workflow# Dara v1.1.2hw — Streamlined XRD and Multi-Database Workflow



**Version**: 1.1.2hw_v0.3  

**Python**: 3.11-3.12 (3.13 not compatible with Ray on Windows)  

**Package Manager**: UV (recommended)**Version**: 1.1.2+hw_v0.2  This README focuses on what’s new in 1.1.2hw and how to use Dara quickly. Advanced database rebuild (全量更新) instructions are at the end. For the legacy landing page, see `README_original.md`.



This README focuses on the new local web server interface and quick start guide. For the original Dara documentation, see legacy files in `docs/`.**Python**: ≥3.10 (tested on 3.10-3.13)  



---**Package Manager**: UV (recommended)---



## ⭐ What's New in v0.3



### Critical Bug Fixes---## ⭐ What’s new

- ✅ **Web UI Loading Bug Fixed** - Task results now display correctly without infinite loading spinner

- ✅ **Chemical Formula Display** - All CIF entries show "Formula (ID)" format (e.g., "Y4Mo4O11 (281037)")

- ✅ **Ray Parallel Processing** - Platform-specific dependency for Windows compatibility (Ray 2.50.1)

- ✅ **Python Version Lock** - Restricted to 3.11-3.12 for stable Ray support on Windows## ⭐ What's New- Unified multi-database workflow (ICSD, COD, MP) with one streamlined notebook

- ✅ **Import Path Fixes** - Resolved database_interface module import issues in scripts

- 🚀 **Production Ready** - Full validation with fresh clone testing- MP integration with experimental/theoretical labels and stability filtering



### Previous Features (v0.2)- **Unified multi-database workflow** (ICSD, COD, MP) with streamlined notebook- UV-based reproducible setup; helpers to build/verify indexes

- **Unified multi-database workflow** - ICSD, COD, Materials Project in one interface

- **Materials Project integration** - Experimental/theoretical classification and stability filtering- **Materials Project integration** with experimental/theoretical classification and stability filtering  - Original Dara functions fully retained, including XRD automatic search phase and refinement

- **UV-based setup** - One command to install all dependencies

- **Chemical system filtering** - Automatically includes all subsystems (unary, binary, ternary)- **UV-based reproducible environment** - one command setup with all dependencies- Rights reserved by original developers of Dara and databases

- **Original Dara functions** - XRD automatic search phase and refinement fully retained

- **Chemical system filtering** - automatically includes all subsystems (unary, binary, ternary)

---

- **Dependency verification** - built-in script to validate installation---

## 🌐 Two Web Interfaces

- Original Dara functions fully retained, including XRD automatic search phase and refinement

### 1. **NEW: Dara Local Multi-Database Portal** (Port 8899) ⭐ **RECOMMENDED**

## 🌐 Web Portals

**Features**:

- Multi-database selector (COD / ICSD / MP)### Original Dara Web Portal (Port 8898)

- Custom CIF upload support

- Chemical system filtering with automatic subsystem inclusion- Launch the upstream FastAPI + Gatsby UI with the built-in CLI:

- Asynchronous job queue with background workers

- Enhanced result display with chemical formulas```powershell

uv run python -m dara.cli server --host 127.0.0.1 --port 8898

**Start Server**:```

```powershell

# Option 1: Direct Python- Open a browser at `http://localhost:8898` to use the legacy reaction-predictor workflow.

.venv\Scripts\python.exe launch_local_server.py- Submit jobs with `POST /api/submit` (see `docs/web_server.md` for API details). Poll status via `GET /api/task/{wf_id}` or browse queued jobs at `/tasks` in the UI.

- Optional: export `MP_API_KEY=<your-key>` before starting to enable Materials Project reaction prediction.

# Option 2: Using UV

uv run python launch_local_server.py### Dara Local Multi-Database Portal (Port 8899)

```

- Launch the extended local copy (COD / ICSD / MP selector) with:

**Access**: Open browser at `http://localhost:8899`

```powershell

**API Usage**:uv run python launch_local_server.py

- Submit search: `POST /api/search` (returns workflow ID immediately)```

- Check status: `GET /api/task/{workflow_id}`

- List all tasks: `GET /api/tasks`- The server boots on `http://localhost:8899` and automatically spawns its queue worker.

- Submit searches with `POST /api/search` and poll results with `GET /api/task/{wf_id}`. Each request is queued, so the API returns immediately with a workflow ID.

**Example**: See `example_api_usage_async.py` for ready-to-run polling client.- Use `example_api_usage_async.py` for a ready-to-run polling client, or inspect `JOB_QUEUE_INTEGRATION.md` for the async workflow and job-queue architecture.

- Custom CIF uploads and chemical-system filtering are supported; CIFs are cleaned up automatically after job completion.

**Architecture**: See `JOB_QUEUE_INTEGRATION.md` for job queue design details.

---

### 2. Original Dara Web Portal (Port 8898)

## 1) Quick Start (recommended path)

**Features**:

- Legacy reaction-predictor workflow---

- Materials Project reaction prediction (requires `MP_API_KEY`)

1. Environment setup (uv)

**Start Server**:

```powershell## 🚀 Quick Start

uv run python -m dara.cli server --host 127.0.0.1 --port 8898

``````powershell



**Access**: Open browser at `http://localhost:8898`### 1. Install UV Package Managergit clone https://github.com/idocx/dara.git



**API**: See `docs/web_server.md` for API documentation.cd dara



---**Windows (PowerShell)**:



## 🚀 Quick Start```powershelluv venv .venv --python 3.11



### 1. Install UV Package Managerpowershell -c "irm https://astral.sh/uv/install.ps1 | iex".\.venv\Scripts\Activate.ps1



**Windows (PowerShell)**:```

```powershell

powershell -c "irm https://astral.sh/uv/install.ps1 | iex"uv pip install -e ".[docs]"

```

**macOS/Linux**:uv pip install jupyterlab ipykernel

**macOS/Linux**:

```bash```bashpython -m ipykernel install --user --name=dara-uv --display-name="Dara (uv)"

curl -LsSf https://astral.sh/uv/install.sh | sh

```curl -LsSf https://astral.sh/uv/install.sh | sh```



### 2. Clone Repository```



```bash2. Place existing databases and indexes (do not add to Git)

git clone https://github.com/harvey-dai-haiwen/dara_hw.git

cd dara### 2. Setup Environment

```

```

### 3. Setup Environment

```bashdara/

```powershell

# Create virtual environment with Python 3.11# Clone repository├── cod_cifs/                  # COD CIF files (≈100 GB)

uv venv .venv --python 3.11

git clone https://github.com/harvey-dai-haiwen/dara_hw.git├── icsd_cifs/                 # ICSD CIF files (≈10 GB)

# Activate environment

.\.venv\Scripts\Activate.ps1  # Windows PowerShellcd dara├── mp_cifs/                   # MP CIF files (~2 GB)

# source .venv/bin/activate    # Linux/macOS

└── indexes/

# Install all dependencies (includes Ray, pymatgen, etc.)

uv pip install -e .# Install all dependencies (one command!)    ├── cod_index_filled.parquet



# Optional: Verify installationuv sync    ├── icsd_index_filled.parquet

uv run python verify_dependencies.py

```    ├── mp_index.parquet



**Expected output**:# Verify installation (optional)    └── merged_index.parquet

```

✅ All critical dependencies are available! (27/27 packages OK)uv run python verify_dependencies.py```

```

```

### 4. Place Database Files

Optional: link external data folders using symlinks on Windows PowerShell (Admin):

Place your database CIF files and indices (not tracked by Git):

**Expected output**:

```

dara/``````powershell

├── cod_cifs/                  # COD CIF files (≈100 GB)

├── icsd_cifs/                 # ICSD CIF files (≈10 GB)✅ All critical dependencies are available! (27/27 packages OK)New-Item -ItemType SymbolicLink -Path .\cod_cifs -Target "D:\\Data\\COD\\cifs"

├── mp_cifs/                   # MP CIF files (~2 GB)

└── indexes/```New-Item -ItemType SymbolicLink -Path .\icsd_cifs -Target "D:\\Data\\ICSD\\cifs"

    ├── cod_index_filled.parquet    (~80 MB, 502K entries)

    ├── icsd_index_filled.parquet   (~50 MB, 229K entries)New-Item -ItemType SymbolicLink -Path .\mp_cifs   -Target "D:\\Data\\MP\\cifs"

    ├── mp_index.parquet            (~30 MB, 169K entries)

    └── merged_index.parquet        (~280 MB combined)### 3. Place Database Files```

```



**Optional**: Link external data folders using symlinks:

Place your database CIF files and indices (not tracked by Git):3. Verify data presence

**Windows (PowerShell Admin)**:

```powershell

New-Item -ItemType SymbolicLink -Path .\cod_cifs -Target "D:\Data\COD\cifs"

New-Item -ItemType SymbolicLink -Path .\icsd_cifs -Target "D:\Data\ICSD\cifs"``````powershell

New-Item -ItemType SymbolicLink -Path .\mp_cifs -Target "D:\Data\MP\cifs"

```dara/python .\scripts\check_data_status.py



**Linux/macOS**:├── cod_cifs/                  # COD CIF files (≈100 GB)```

```bash

ln -s /path/to/COD/cifs cod_cifs├── icsd_cifs/                 # ICSD CIF files (≈10 GB)

ln -s /path/to/ICSD/cifs icsd_cifs

ln -s /path/to/MP/cifs mp_cifs├── mp_cifs/                   # MP CIF files (~2 GB)4. Run the streamlined notebook

```

└── indexes/

### 5. Verify Data Status

    ├── cod_index_filled.parquet```powershell

```powershell

uv run python scripts/check_data_status.py    ├── icsd_index_filled.parquetjupyter lab

```

    ├── mp_index.parquet```

### 6. Start Using Dara

    └── merged_index.parquet

**Option A: Web Interface (Recommended)**

```powershell```Open `notebooks/streamlined_phase_analysis.ipynb`, select the "Dara (uv)" kernel, and run:

# Start the new local server

uv run python launch_local_server.py- Part 1: Pattern + environment configuration



# Open browser at http://localhost:8899**Optional**: Link external data folders using symlinks:- Part 2: Single-database phase search (COD/ICSD/MP/NONE) + exports

# Upload XRD pattern, select database, run analysis

```- Part 3: BGMN refinement + exports



**Option B: Jupyter Notebook****Windows (PowerShell Admin)**:

```powershell

# Install Jupyter (if not already done)```powershellReports are saved under `~/Documents/dara_analysis/<ChemicalSystem>/reports/`.

uv pip install jupyterlab ipykernel

New-Item -ItemType SymbolicLink -Path .\cod_cifs -Target "D:\Data\COD\cifs"

# Create kernel

python -m ipykernel install --user --name=dara-uv --display-name="Dara (uv)"New-Item -ItemType SymbolicLink -Path .\icsd_cifs -Target "D:\Data\ICSD\cifs"More environment details and troubleshooting: `docs/environment_setup.md`.



# Start JupyterNew-Item -ItemType SymbolicLink -Path .\mp_cifs -Target "D:\Data\MP\cifs"

uv run jupyter lab

``````---



Open `notebooks/streamlined_phase_analysis.ipynb` and run:

- **Part 1**: XRD pattern loading and environment configuration

- **Part 2**: Database selection + Phase search + Visualization + Export**Linux/macOS**:---

- **Part 3**: BGMN Rietveld refinement with custom parameters

```bash

Reports are automatically saved to `~/Documents/dara_analysis/<ChemicalSystem>/reports/`.

ln -s /path/to/COD/cifs cod_cifs## 🔧 Useful utilities

**Option C: Original Web Portal**

```powershellln -s /path/to/ICSD/cifs icsd_cifs

# Start legacy server

uv run python -m dara.cli server --host 127.0.0.1 --port 8898ln -s /path/to/MP/cifs mp_cifs- `scripts/dara_adapter.py` – prepare CIF path lists for DARA `additional_phases`



# Open browser at http://localhost:8898```- `scripts/database_interface.py` – unified filters across ICSD/COD/MP

```

- `scripts/list_xrd_elements.py` – regenerate `dataset/xrd_elements.csv`

---

### 4. Verify Data Status- Helpers:

## 🔧 Useful Utilities

    - `scripts/setup_databases.ps1` – one-shot database setup (Windows PowerShell)

Located in `scripts/`:

```bash    - `scripts/check_data_status.py` – sanity check for indexes and CIF folders

- **`dara_adapter.py`** – Prepare filtered CIF lists for DARA `additional_phases`

- **`database_interface.py`** – Unified filtering across ICSD/COD/MP databasesuv run python scripts/check_data_status.py

- **`check_data_status.py`** – Verify database indices and CIF folders

- **`verify_dependencies.py`** – Validate Python environment```---

- **`list_xrd_elements.py`** – Regenerate `dataset/xrd_elements.csv`



**Windows PowerShell Helper**:

- **`setup_databases.ps1`** – One-shot database setup script### 5. Run Analysis## 🛡 Keep large data out of Git



---



## 🛡️ Data ManagementStart Jupyter and open the streamlined notebook:We ignore CIF folders and indexes by default via `.gitignore`:



### .gitignore Configuration



Large data files are excluded from Git by default:```bash```



```gitignoreuv run jupyter labcod_cifs/

# Database files (NOT tracked)

cod_cifs/```icsd_cifs/

icsd_cifs/

mp_cifs/mp_cifs/

indexes/

*.cifOpen `notebooks/streamlined_phase_analysis.ipynb` and run:indexes/



# Local runtime data- **Part 1**: XRD pattern and setup*.cif

worker_db/

result_store/- **Part 2**: Database selection + Phase search + Visualization```



# Test files- **Part 3**: Advanced refinement with custom parameters

test_*.py

check_*.pyIf some were accidentally tracked, run (keep local files):

debug_*.py

*.ps1Reports are automatically saved to `~/Documents/dara_analysis/<ChemicalSystem>/reports/`.



# Exception: Keep one debug notebook```powershell

!notebooks/debug_web_api_cifs.ipynb

```---git rm -r --cached cod_cifs icsd_cifs mp_cifs indexes



### Remove Accidentally Tracked Filesgit commit -m "chore: untrack large datasets; keep files locally"



If database files were accidentally committed:## 📖 Documentation```



```powershell

# Remove from Git but keep local files

git rm -r --cached cod_cifs icsd_cifs mp_cifs indexes- **UV Setup Guide**: `UV_SETUP_GUIDE.md` - Detailed environment setup and troubleshooting---

git commit -m "chore: untrack large datasets; keep files locally"

```- **Environment Setup**: `docs/environment_setup.md` - Python environment configuration



---- **Database Update**: `docs/database_update.md` - Full database rebuild instructions## 🧠 Advanced: Rebuild databases (全量更新)



## 🔬 Advanced: Database Rebuild (全量更新)- **Tutorials**: `docs/tutorials.md` - Example workflows



Full database indexing instructions are available in `docs/database_update.md`.- **CHANGELOG**: `CHANGELOG.md` - Version history and changesAll scripts live in `scripts/`. Summary commands for Windows PowerShell are shown; see `docs/database_update.md` for full instructions and validation steps.



### Quick Reference



**ICSD**:---### ICSD index

```powershell

# 1) Build raw index```powershell

python scripts/index_icsd.py \

    --csv "D:\Data\ICSD\[Kedar_Group_ONLY]_ICSD2024_summary_2024.2_v5.3.0.csv" \## 🔧 Useful Utilities# 1) Build raw index

    --out indexes/icsd_index.parquet

python scripts/index_icsd.py \

# 2) Extract CIFs + fill spacegroups

python scripts/extract_icsd_cifs.py \Located in `scripts/`:    --csv "D:\\Data\\ICSD\\[Kedar_Group_ONLY]_ICSD2024_summary_2024.2_v5.3.0.csv" \

    --csv "D:\Data\ICSD\[Kedar_Group_ONLY]_ICSD2024_summary_2024.2_v5.3.0.csv" \

    --index indexes/icsd_index.parquet \    --out indexes/icsd_index.parquet

    --cif-dir icsd_cifs \

    --out indexes/icsd_index_filled.parquet- **`dara_adapter.py`** – Prepare filtered CIF lists for DARA phase search

```

- **`database_interface.py`** – Unified filtering across ICSD/COD/MP databases# 2) Extract CIFs + fill spacegroups

**COD**:

```powershell- **`check_data_status.py`** – Verify database indices and CIF folderspython scripts/extract_icsd_cifs.py \

# 1) Extract COD archive

tar -xJf D:\Data\COD\cod-cifs-mysql.txz -C cod_cifs- **`verify_dependencies.py`** – Validate Python environment    --csv "D:\\Data\\ICSD\\[Kedar_Group_ONLY]_ICSD2024_summary_2024.2_v5.3.0.csv" \



# 2) Build parallel index (16 workers)- **`list_xrd_elements.py`** – Regenerate `dataset/xrd_elements.csv`    --index indexes/icsd_index.parquet \

python scripts/index_cod_parallel.py \

    --cif-dir cod_cifs \    --cif-dir icsd_cifs \

    --out indexes/cod_index.parquet \

    --workers 16**Windows PowerShell Helper**:    --out indexes/icsd_index_filled.parquet



# 3) Fill spacegroups (sequential for stability)- **`setup_databases.ps1`** – One-shot database setup script```

python scripts/fill_spacegroup_cod.py \

    --index indexes/cod_index.parquet \

    --cif-dir cod_cifs \

    --out indexes/cod_index_filled.parquet \---### COD index

    --workers 1

``````powershell



**Materials Project**:## 🛡️ Data Management# 1) Extract COD archive

```powershell

python scripts/index_mp.py \tar -xJf D:\\Data\\COD\\cod-cifs-mysql.txz -C cod_cifs

    --input "D:\Data\MP\df_MP_20250211.pkl" \

    --output indexes/mp_index.parquet \### .gitignore Configuration

    --cif-dir mp_cifs

```# 2) Build parallel index



**Merge Indices**:Large data files are excluded from Git by default:python scripts/index_cod_parallel.py \

```powershell

python scripts/merge_indices.py \    --cif-dir cod_cifs \

    --parquets indexes/icsd_index_filled.parquet indexes/cod_index_filled.parquet indexes/mp_index.parquet \

    --out-parquet indexes/merged_index.parquet \```gitignore    --out indexes/cod_index.parquet \

    --out-json indexes/merged_index.json.gz \

    --out-sqlite indexes/merged_index.sqlitecod_cifs/    --workers 16

```

icsd_cifs/

**Validation**:

```powershellmp_cifs/# 3) Fill spacegroups (sequential for stability)

python scripts/verify_indices.py

python scripts/verify_mp_index.pyindexes/python scripts/fill_spacegroup_cod.py \

python scripts/verify_merged.py

```*.cif    --index indexes/cod_index.parquet \



---```    --cif-dir cod_cifs \



## 🐛 Troubleshooting    --out indexes/cod_index_filled.parquet \



### Ray Issues on Windows### Remove Accidentally Tracked Files    --workers 1



**Problem**: `ray>=2.51.0` has no Windows wheels```



**Solution**: The project now uses platform-specific dependencies:If database files were accidentally committed:

- Windows: `ray>=2.10.0,<2.51.0` (tested with 2.50.1)

- Linux/macOS: `ray>=2.51.0`### Materials Project (MP) index



This is automatically handled by `pyproject.toml`.```bash```powershell



### Python 3.13 Compatibility# Remove from Git but keep local filespython scripts/index_mp.py \



**Problem**: Ray doesn't support Python 3.13 on Windowsgit rm -r --cached cod_cifs icsd_cifs mp_cifs indexes    --input "D:\\Data\\MP\\df_MP_20250211.pkl" \



**Solution**: Use Python 3.11 or 3.12:git commit -m "chore: untrack large datasets; keep files locally"    --output indexes/mp_index.parquet \

```powershell

uv venv .venv --python 3.11```    --cif-dir mp_cifs

```

```

### Import Errors

---

**Problem**: `ModuleNotFoundError: No module named 'scripts.database_interface'`

### Merge indices

**Solution**: This is fixed in v0.3 with fallback import mechanism in `scripts/dara_adapter.py`.

## 🔬 Advanced: Database Rebuild```powershell

### Web UI Loading Forever

python scripts/merge_indices.py \

**Problem**: Task results show infinite loading spinner

Full database indexing instructions are available in `docs/database_update.md`.    --parquets indexes/icsd_index_filled.parquet indexes/cod_index_filled.parquet indexes/mp_index.parquet \

**Solution**: Fixed in v0.3. Update to latest version:

```powershell    --out-parquet indexes/merged_index.parquet \

git pull origin main

uv pip install -e .### Quick Reference    --out-json indexes/merged_index.json.gz \

```

    --out-sqlite indexes/merged_index.sqlite

### Missing Chemical Formulas

**ICSD**:```

**Problem**: CIF entries show only numeric IDs

```bash

**Solution**: Fixed in v0.3. Results now display "Formula (ID)" format (e.g., "Y4Mo4O11 (281037)").

# Build index and extract CIFsValidate with: `scripts/verify_indices.py`, `verify_mp_index.py`, and `verify_merged.py`.

---

uv run python scripts/index_icsd.py --csv <ICSD_CSV> --out indexes/icsd_index.parquet

## 📖 Documentation

uv run python scripts/extract_icsd_cifs.py --index indexes/icsd_index.parquet --cif-dir icsd_cifsFull docs: `docs/database_update.md` and `docs/environment_setup.md`.

- **UV Setup Guide**: `UV_SETUP_GUIDE.md` - Detailed environment setup and troubleshooting

- **Environment Setup**: `docs/environment_setup.md` - Python environment configuration```

- **Database Update**: `docs/database_update.md` - Full database rebuild instructions

- **Tutorials**: `docs/tutorials.md` - Example workflows**COD**:

- **Job Queue Integration**: `JOB_QUEUE_INTEGRATION.md` - Async job queue architecture```bash

- **CHANGELOG**: `CHANGELOG.md` - Version history and changes# Extract archive and build index

tar -xJf cod-cifs-mysql.txz -C cod_cifs

---uv run python scripts/index_cod_parallel.py --cif-dir cod_cifs --out indexes/cod_index.parquet

uv run python scripts/fill_spacegroup_cod.py --index indexes/cod_index.parquet --out indexes/cod_index_filled.parquet

## 📦 Alternative Installation (pip)```



If you prefer traditional pip installation:**Materials Project**:

```bash

```bashuv run python scripts/index_mp.py --input <MP_PKL> --output indexes/mp_index.parquet --cif-dir mp_cifs

# Create virtual environment with Python 3.11```

python3.11 -m venv .venv

source .venv/bin/activate  # Linux/macOS**Merge Indices**:

# .\.venv\Scripts\Activate.ps1  # Windows```bash

uv run python scripts/merge_indices.py \

# Install package    --parquets indexes/icsd_index_filled.parquet indexes/cod_index_filled.parquet indexes/mp_index.parquet \

pip install -e .    --out-parquet indexes/merged_index.parquet

```

# Optional: Install Jupyter

pip install jupyterlab ipykernel---

```

## 📦 Alternative Installation (pip)

---

If you prefer traditional pip installation:

## 📄 License

```bash

MIT License - See `LICENSE` file for details.python -m venv .venv

source .venv/bin/activate  # Linux/macOS

Original Dara developed by Yuxing Fei and Matthew McDermott.  # .\.venv\Scripts\Activate.ps1  # Windows

This fork (dara_hw) maintained by Harvey Dai.

pip install -e ".[docs]"

---pip install jupyterlab ipykernel

```

## 🙏 Acknowledgments

---

- **Original Dara developers**: Yuxing Fei, Matthew McDermott

- **Database sources**: ICSD, COD, Materials Project## 📄 License

- **BGMN Rietveld refinement engine**

- **Dependencies**: Ray (parallel processing), pymatgen (structure analysis), FastAPI (web server)MIT License - See `LICENSE` file for details.



---Original Dara developed by Yuxing Fei and Matthew McDermott.  

This fork (dara_hw) maintained by Harvey Dai.

## 📞 Support

---

For issues, questions, or contributions:

- **GitHub Issues**: [harvey-dai-haiwen/dara_hw](https://github.com/harvey-dai-haiwen/dara_hw/issues)## 🙏 Acknowledgments

- **Documentation**: Check `docs/` folder for detailed guides

- **Example Scripts**: See `example_api_usage_async.py` for API usage patterns- Original Dara developers: Yuxing Fei, Matthew McDermott

- Database sources: ICSD, COD, Materials Project

---- BGMN Rietveld refinement engine



**Quick Links**:---

- 🚀 [Quick Start](#-quick-start)

- 🌐 [Web Interfaces](#-two-web-interfaces)For detailed documentation, see:

- 🔧 [Utilities](#-useful-utilities)- **Quick Start**: This README

- 🔬 [Database Rebuild](#-advanced-database-rebuild-全量更新)- **Full Setup**: `UV_SETUP_GUIDE.md`

- 🐛 [Troubleshooting](#-troubleshooting)- **Database Management**: `docs/database_update.md`

- **Troubleshooting**: `docs/environment_setup.md`
