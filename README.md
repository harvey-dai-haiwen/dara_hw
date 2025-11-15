# Dara v1.1.2hw_v0.3 — XRD Phase Analysis with Multi-Database Support# Dara v1.1.2hw_v0.3 — XRD Phase Analysis with Multi-Database Support# Dara v1.1.2hw — Streamlined XRD and Multi-Database Workflow# Dara v1.1.2hw — Streamlined XRD and Multi-Database Workflow



**Version**: 1.1.2hw_v0.3  

**Python**: 3.11-3.12 (Ray compatibility requirement)  

**Package Manager**: UV (recommended)**Version**: 1.1.2hw_v0.3  



This README focuses on the new local web server interface and quick start guide. For the original Dara documentation, see legacy files in `docs/`.**Python**: 3.11-3.12 (3.13 not compatible with Ray on Windows)  



---**Package Manager**: UV (recommended)**Version**: 1.1.2+hw_v0.2  This README focuses on what’s new in 1.1.2hw and how to use Dara quickly. Advanced database rebuild (全量更新) instructions are at the end. For the legacy landing page, see `README_original.md`.



## ⭐ What's New in v0.3



### UI ImprovementsThis README focuses on the new local web server interface and quick start guide. For the original Dara documentation, see legacy files in `docs/`.**Python**: ≥3.10 (tested on 3.10-3.13)  

- ✅ **Full English Localization** - All Chinese text replaced with English in web interface

- ✅ **Interactive Tutorial** - Step-by-step guide at `/search-tutorial`

- ✅ **Improved Search Interface** - Clear labels, helpful tooltips, and streamlined workflow

- ✅ **Windows Compatibility** - Fixed console encoding and build script issues---**Package Manager**: UV (recommended)---



### Critical Bug Fixes

- ✅ **Web UI Loading Bug** - Task results now display correctly without infinite loading spinner

- ✅ **Chemical Formula Display** - All CIF entries show "Formula (ID)" format (e.g., "Y4Mo4O11 (281037)")## ⭐ What's New in v0.3

- ✅ **Ray Parallel Processing** - Platform-specific dependency for Windows (Ray 2.50.1)

- ✅ **Python Version Lock** - Restricted to 3.11-3.12 for stable Ray support on Windows

- ✅ **Import Path Fixes** - Resolved `database_interface` module import issues in scripts

### Critical Bug Fixes---## ⭐ What’s new

### Key Features (from v0.2)

- **Unified multi-database workflow** - ICSD, COD, Materials Project in one interface- ✅ **Web UI Loading Bug Fixed** - Task results now display correctly without infinite loading spinner

- **Materials Project integration** - Experimental/theoretical classification and stability filtering

- **UV-based setup** - One command to install all dependencies- ✅ **Chemical Formula Display** - All CIF entries show "Formula (ID)" format (e.g., "Y4Mo4O11 (281037)")

- **Chemical system filtering** - Automatically includes all subsystems (unary, binary, ternary)

- **Original Dara functions** - XRD automatic search phase and refinement fully retained- ✅ **Ray Parallel Processing** - Platform-specific dependency for Windows compatibility (Ray 2.50.1)



---- ✅ **Python Version Lock** - Restricted to 3.11-3.12 for stable Ray support on Windows## ⭐ What's New- Unified multi-database workflow (ICSD, COD, MP) with one streamlined notebook



## 🚀 Quick Start- ✅ **Import Path Fixes** - Resolved database_interface module import issues in scripts



### Prerequisites- 🚀 **Production Ready** - Full validation with fresh clone testing- MP integration with experimental/theoretical labels and stability filtering

- **Python**: 3.11 or 3.12 (3.13 not compatible with Ray on Windows)

- **UV package manager**: [Installation guide](https://docs.astral.sh/uv/getting-started/installation/)



### Installation### Previous Features (v0.2)- **Unified multi-database workflow** (ICSD, COD, MP) with streamlined notebook- UV-based reproducible setup; helpers to build/verify indexes



```bash- **Unified multi-database workflow** - ICSD, COD, Materials Project in one interface

# Clone the repository

git clone https://github.com/harvey-dai-haiwen/dara_hw.git- **Materials Project integration** - Experimental/theoretical classification and stability filtering- **Materials Project integration** with experimental/theoretical classification and stability filtering  - Original Dara functions fully retained, including XRD automatic search phase and refinement

cd dara_hw

- **UV-based setup** - One command to install all dependencies

# Install dependencies with UV

uv sync- **Chemical system filtering** - Automatically includes all subsystems (unary, binary, ternary)- **UV-based reproducible environment** - one command setup with all dependencies- Rights reserved by original developers of Dara and databases



# Verify installation- **Original Dara functions** - XRD automatic search phase and refinement fully retained

uv run python verify_dependencies.py

```- **Chemical system filtering** - automatically includes all subsystems (unary, binary, ternary)



### Launch the Dara Local v2 Web UI

```bash
# Start the Dara Local v2 phase-search web server (Port 8899)
uv run python launch_local_server.py
```

Server will start at: **http://localhost:8899**.

- Open **`/search`** to upload an XRD pattern and configure Part 1 + Part 2 parameters.
- Use **`/results`** to see the job queue; open **`/results/{jobId}`** for full diagnostics,
  Plotly fits, phase tables, and ZIP report downloads.
- The **Tutorial** link in the top navigation explains how this maps to
  `streamlined_phase_analysis_K2SnTe5.ipynb` Part 1 & 2.

> **Note (deprecation)**: the old `dara_local` v1 server and its routes (e.g. `/task`,
> `/search-tutorial`) are deprecated and the code has been removed in this fork.
> Use Dara Local v2 instead via `launch_local_server.py`.

---

### Original Dara Web Portal (Port 8898)



---- Chemical system filtering with automatic subsystem inclusion- Launch the upstream FastAPI + Gatsby UI with the built-in CLI:



## 🌐 Two Web Interfaces- Asynchronous job queue with background workers



### 1. **NEW: Dara Local Multi-Database Portal** (Port 8899) ⭐ **RECOMMENDED**- Enhanced result display with chemical formulas```powershell



**Features**:uv run python -m dara.cli server --host 127.0.0.1 --port 8898

- Multi-database selector (COD / ICSD / MP)

- Custom CIF upload support**Start Server**:```

- Chemical system filtering with automatic subsystem inclusion

- Asynchronous job queue with background workers```powershell

- Enhanced result display with chemical formulas

- Interactive tutorial at `/search-tutorial`# Option 1: Direct Python- Open a browser at `http://localhost:8898` to use the legacy reaction-predictor workflow.



**Launch**:.venv\Scripts\python.exe launch_local_server.py- Submit jobs with `POST /api/submit` (see `docs/web_server.md` for API details). Poll status via `GET /api/task/{wf_id}` or browse queued jobs at `/tasks` in the UI.

```bash

uv run python launch_local_server.py- Optional: export `MP_API_KEY=<your-key>` before starting to enable Materials Project reaction prediction.

```

# Option 2: Using UV

**Access**: http://localhost:8899

uv run python launch_local_server.py### Dara Local Multi-Database Portal (Port 8899)

### 2. Original Dara Web Portal (Port 8898)

```

Legacy interface with original reaction predictor functionality.

- Launch the extended local copy (COD / ICSD / MP selector) with:

**Launch**:

```bash**Access**: Open browser at `http://localhost:8899`

uv run python -m dara.cli server --host 127.0.0.1 --port 8898

``````powershell



**Access**: http://localhost:8898**API Usage**:uv run python launch_local_server.py



---- Submit search: `POST /api/search` (returns workflow ID immediately)```



## 📖 Documentation- Check status: `GET /api/task/{workflow_id}`



- **Tutorial**: http://localhost:8899/search-tutorial (after starting server)- List all tasks: `GET /api/tasks`- The server boots on `http://localhost:8899` and automatically spawns its queue worker.

- **Launch Instructions**: See `LAUNCH_INSTRUCTIONS.md` for detailed setup

- **UV Setup Guide**: See `UV_SETUP_GUIDE.md` for environment management- Submit searches with `POST /api/search` and poll results with `GET /api/task/{wf_id}`. Each request is queued, so the API returns immediately with a workflow ID.

- **Changelog**: See `CHANGELOG.md` for version history

- **Original Docs**: Legacy documentation in `docs/` directory**Example**: See `example_api_usage_async.py` for ready-to-run polling client.- Use `example_api_usage_async.py` for a ready-to-run polling client, or inspect `JOB_QUEUE_INTEGRATION.md` for the async workflow and job-queue architecture.



---- Custom CIF uploads and chemical-system filtering are supported; CIFs are cleaned up automatically after job completion.



## 🗄️ Database Setup**Architecture**: See `JOB_QUEUE_INTEGRATION.md` for job queue design details.



The server requires indexed databases in the following locations:---



```### 2. Original Dara Web Portal (Port 8898)

dara_hw/

├── indexes/## 1) Quick Start (recommended path)

│   ├── cod_index.parquet

│   ├── icsd_index.parquet**Features**:

│   └── mp_index.parquet

├── cod_cifs/cif/- Legacy reaction-predictor workflow---

├── icsd_cifs/cif/

└── mp_cifs/{0-9,m}/- Materials Project reaction prediction (requires `MP_API_KEY`)

```

1. Environment setup (uv)

### Quick Database Setup

**Start Server**:

For testing, you can use a subset of databases. See `notebooks/mp_database_tutorial.ipynb` for Materials Project setup instructions.

```powershell## 🚀 Quick Start

For full database rebuild instructions, see the **Database Rebuild** section at the end of this README.

uv run python -m dara.cli server --host 127.0.0.1 --port 8898

---

``````powershell

## 🔧 Troubleshooting



### Python Version Issues

**Access**: Open browser at `http://localhost:8898`### 1. Install UV Package Managergit clone https://github.com/idocx/dara.git

```bash

# Check Python version

uv run python --version

**API**: See `docs/web_server.md` for API documentation.cd dara

# Should output: Python 3.11.x or 3.12.x

```



If using Python 3.13, install Python 3.11 or 3.12 and recreate the environment.---**Windows (PowerShell)**:



### Ray Import Errors



On Windows, ensure you have Ray 2.50.1:## 🚀 Quick Start```powershelluv venv .venv --python 3.11

```bash

uv run python -c "import ray; print(ray.__version__)"

```

### 1. Install UV Package Managerpowershell -c "irm https://astral.sh/uv/install.ps1 | iex".\.venv\Scripts\Activate.ps1

If issues persist, try:

```bash

uv sync --reinstall-package ray

```**Windows (PowerShell)**:```



### UI Not Loading```powershell



If the web interface shows errors:powershell -c "irm https://astral.sh/uv/install.ps1 | iex"uv pip install -e ".[docs]"

1. Check server logs for error messages

2. Verify database index files exist```

3. Clear browser cache and reload

**macOS/Linux**:uv pip install jupyterlab ipykernel

### Import Module Errors

**macOS/Linux**:

If you see `ModuleNotFoundError: No module named 'dara_local'`:

```bash```bash```bashpython -m ipykernel install --user --name=dara-uv --display-name="Dara (uv)"

# Ensure you're in the project root directory

cd D:\path\to\dara_hwcurl -LsSf https://astral.sh/uv/install.sh | sh



# Reinstall dependencies```curl -LsSf https://astral.sh/uv/install.sh | sh```

uv sync

```



---### 2. Clone Repository```



## 🧪 Development



### Running Tests```bash2. Place existing databases and indexes (do not add to Git)



```bashgit clone https://github.com/harvey-dai-haiwen/dara_hw.git

# Run all tests

uv run pytest tests/cd dara### 2. Setup Environment



# Run specific test file```

uv run pytest tests/test_api.py

``````



### Dependency Verification### 3. Setup Environment



```bash```bashdara/

# Verify all dependencies are installed

uv run python verify_dependencies.py```powershell

```

# Create virtual environment with Python 3.11# Clone repository├── cod_cifs/                  # COD CIF files (≈100 GB)

---

uv venv .venv --python 3.11

## 📋 System Requirements

git clone https://github.com/harvey-dai-haiwen/dara_hw.git├── icsd_cifs/                 # ICSD CIF files (≈10 GB)

- **OS**: Windows, macOS, or Linux

- **Python**: 3.11 or 3.12 (3.13 not supported due to Ray compatibility)# Activate environment

- **RAM**: 8GB minimum, 16GB recommended for large databases

- **Disk Space**: 50GB+ for full databases (COD + ICSD + MP).\.venv\Scripts\Activate.ps1  # Windows PowerShellcd dara├── mp_cifs/                   # MP CIF files (~2 GB)

- **UV**: Latest version recommended

# source .venv/bin/activate    # Linux/macOS

---

└── indexes/

## 🤝 Contributing

# Install all dependencies (includes Ray, pymatgen, etc.)

This is a hardware-lab tailored fork of the original Dara project. For contributions:

uv pip install -e .# Install all dependencies (one command!)    ├── cod_index_filled.parquet

1. Fork the repository

2. Create a feature branch

3. Make your changes

4. Submit a pull request# Optional: Verify installationuv sync    ├── icsd_index_filled.parquet



---uv run python verify_dependencies.py



## 📜 License & Credits```    ├── mp_index.parquet



**Rights reserved by original developers of Dara and databases.**



- **Dara**: Original XRD phase analysis framework**Expected output**:# Verify installation (optional)    └── merged_index.parquet

- **COD**: Crystallography Open Database

- **ICSD**: Inorganic Crystal Structure Database```

- **MP**: Materials Project

✅ All critical dependencies are available! (27/27 packages OK)uv run python verify_dependencies.py```

This fork (v1.1.2hw) adds multi-database workflow improvements while preserving all original functionality.

```

---

```

## 🔨 Database Rebuild (Advanced)

### 4. Place Database Files

<details>

<summary>Click to expand full database rebuild instructions</summary>Optional: link external data folders using symlinks on Windows PowerShell (Admin):



### COD Database SetupPlace your database CIF files and indices (not tracked by Git):



1. **Download COD CIF files**:**Expected output**:

   ```bash

   # Download from http://www.crystallography.net/cod/```

   # Extract to cod_cifs/cif/

   ```dara/``````powershell



2. **Build COD index**:├── cod_cifs/                  # COD CIF files (≈100 GB)

   ```bash

   uv run python scripts/index_cod_parallel.py├── icsd_cifs/                 # ICSD CIF files (≈10 GB)✅ All critical dependencies are available! (27/27 packages OK)New-Item -ItemType SymbolicLink -Path .\cod_cifs -Target "D:\\Data\\COD\\cifs"

   ```

├── mp_cifs/                   # MP CIF files (~2 GB)

3. **Verify**:

   ```bash└── indexes/```New-Item -ItemType SymbolicLink -Path .\icsd_cifs -Target "D:\\Data\\ICSD\\cifs"

   uv run python scripts/verify_indices.py

   ```    ├── cod_index_filled.parquet    (~80 MB, 502K entries)



### ICSD Database Setup    ├── icsd_index_filled.parquet   (~50 MB, 229K entries)New-Item -ItemType SymbolicLink -Path .\mp_cifs   -Target "D:\\Data\\MP\\cifs"



1. **Export from ICSD**:    ├── mp_index.parquet            (~30 MB, 169K entries)

   - Requires ICSD license

   - Export CIF files to `icsd_cifs/cif/`    └── merged_index.parquet        (~280 MB combined)### 3. Place Database Files```



2. **Build ICSD index**:```

   ```bash

   uv run python scripts/index_icsd.py

   ```

**Optional**: Link external data folders using symlinks:

### Materials Project Setup

Place your database CIF files and indices (not tracked by Git):3. Verify data presence

1. **Get API key** from https://materialsproject.org/api

**Windows (PowerShell Admin)**:

2. **Download structures**:

   ```bash```powershell

   # See notebooks/mp_database_tutorial.ipynb for detailed instructions

   ```New-Item -ItemType SymbolicLink -Path .\cod_cifs -Target "D:\Data\COD\cifs"



3. **Build MP index**:New-Item -ItemType SymbolicLink -Path .\icsd_cifs -Target "D:\Data\ICSD\cifs"``````powershell

   ```bash

   uv run python scripts/index_mp.pyNew-Item -ItemType SymbolicLink -Path .\mp_cifs -Target "D:\Data\MP\cifs"

   ```

```dara/python .\scripts\check_data_status.py

### Merge All Databases



```bash

# Merge all three databases into one unified index**Linux/macOS**:├── cod_cifs/                  # COD CIF files (≈100 GB)```

uv run python scripts/merge_indices.py

``````bash



### Verificationln -s /path/to/COD/cifs cod_cifs├── icsd_cifs/                 # ICSD CIF files (≈10 GB)



```bashln -s /path/to/ICSD/cifs icsd_cifs

# Verify all databases are correctly indexed

uv run python scripts/verify_merged.pyln -s /path/to/MP/cifs mp_cifs├── mp_cifs/                   # MP CIF files (~2 GB)4. Run the streamlined notebook

```

```

</details>

└── indexes/

---

### 5. Verify Data Status

## 📚 Additional Resources

    ├── cod_index_filled.parquet```powershell

- **Original Dara Repository**: https://github.com/idocx/dara

- **UV Documentation**: https://docs.astral.sh/uv/```powershell

- **Materials Project API**: https://materialsproject.org/api

- **COD Database**: http://www.crystallography.net/cod/uv run python scripts/check_data_status.py    ├── icsd_index_filled.parquetjupyter lab



---```



**Version**: 1.1.2hw_v0.3      ├── mp_index.parquet```

**Last Updated**: November 13, 2025  

**Maintainer**: Harvey Dai (harvey-dai-haiwen)### 6. Start Using Dara


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
