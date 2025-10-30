# Environment Setup for MP Database Tutorial

This guide explains how to set up the Python environment to run the Materials Project database tutorial.

---

## Prerequisites

1. **Python 3.10+** (recommended: Python 3.11 or 3.12)
2. **UV package manager** (recommended) or pip
3. **DARA installation** with dependencies
4. **Database indices** (generated or provided)

---

## Option 1: Using UV (Recommended) ⚡

UV is a fast Python package manager that handles virtual environments automatically.

### Install UV
```powershell
# Install UV (if not already installed)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Create Virtual Environment and Install DARA
```powershell
# Navigate to DARA repository
cd C:\Users\kedargroup_ws01\Documents\Haiwen\Repos\dara

# Create virtual environment with UV
uv venv .venv --python 3.11

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install DARA in editable mode with all dependencies
uv pip install -e ".[docs]"

# Install additional packages for notebook
uv pip install jupyter ipywidgets nbformat pandas pyarrow

# Verify installation
python -c "import dara; print(f'DARA version: {dara.__version__}')"
python -c "import pymatgen; print(f'Pymatgen version: {pymatgen.__version__}')"
```

### Register Jupyter Kernel
```powershell
# Install ipykernel
uv pip install ipykernel

# Register the kernel
python -m ipykernel install --user --name=dara-mp --display-name="DARA MP Tutorial"
```

---

## Option 2: Using Conda 🐍

If you prefer Conda (e.g., if you already have Pymatgen_hw environment):

### Create New Environment
```powershell
# Create environment with Python 3.11
conda create -n dara-mp python=3.11 -y
conda activate dara-mp

# Install DARA
cd C:\Users\kedargroup_ws01\Documents\Haiwen\Repos\dara
pip install -e ".[docs]"

# Install additional packages
pip install jupyter ipywidgets nbformat pandas pyarrow

# Register kernel
python -m ipykernel install --user --name=dara-mp --display-name="DARA MP Tutorial"
```

### Or Use Existing Pymatgen_hw Environment
```powershell
# Activate existing environment
conda activate Pymatgen_hw

# Install DARA in editable mode
cd C:\Users\kedargroup_ws01\Documents\Haiwen\Repos\dara
pip install -e .

# Install missing packages if needed
pip install jupyter ipywidgets nbformat
```

---

## Option 3: Using pip (Standard)

```powershell
# Create virtual environment
cd C:\Users\kedargroup_ws01\Documents\Haiwen\Repos\dara
python -m venv .venv

# Activate
.\.venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install DARA
pip install -e ".[docs]"

# Install additional packages
pip install jupyter ipywidgets nbformat pandas pyarrow

# Register kernel
python -m ipykernel install --user --name=dara-mp --display-name="DARA MP Tutorial"
```

---

## Verify Installation

Run this in Python to verify everything is installed:

```python
# Core dependencies
import dara
import pymatgen
import pandas as pd
import pyarrow
import plotly

# DARA modules
from dara import search_phases
from dara.refine import do_refinement_no_saving

# New database tools
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd().parent / 'scripts'))
from dara_adapter import prepare_phases_for_dara
from database_interface import StructureDatabaseIndex

print("✅ All packages installed successfully!")
print(f"DARA version: {dara.__version__}")
print(f"Pymatgen version: {pymatgen.__version__}")
```

---

## Required Database Indices

The tutorial requires the following index files to be generated:

### File Locations
```
dara/
├── indexes/
│   ├── icsd_index_filled.parquet  (229,487 entries, ~8 MB)
│   ├── cod_index_filled.parquet   (501,975 entries, ~35 MB)
│   ├── merged_index.parquet       (731,462 entries, ~42 MB)
│   └── mp_index.parquet           (169,385 entries, ~19 MB) ✨ NEW
├── icsd_cifs/                     (~10 GB)
├── cod_cifs/                      (~102 GB)
└── mp_cifs/                       (~2 GB) ✨ NEW
```

### Generate MP Index (if not already done)
```powershell
# Activate your environment
conda activate dara-mp  # or: .\.venv\Scripts\Activate.ps1

# Generate MP index (takes ~9 minutes)
python scripts/index_mp.py \
  --input "path/to/df_MP_20250211.pkl" \
  --output indexes/mp_index.parquet \
  --cif-dir mp_cifs
```

See `scripts/README.md` for detailed indexing instructions.

---

## Running the Tutorial

### Launch Jupyter Notebook
```powershell
# Activate your environment
conda activate dara-mp  # or: .\.venv\Scripts\Activate.ps1

# Navigate to notebooks directory
cd C:\Users\kedargroup_ws01\Documents\Haiwen\Repos\dara\notebooks

# Launch Jupyter
jupyter notebook
```

### Select Kernel
1. Open `mp_database_tutorial.ipynb`
2. Click "Kernel" → "Change kernel" → "DARA MP Tutorial"
3. Run cells sequentially

### Alternative: VS Code
1. Open `mp_database_tutorial.ipynb` in VS Code
2. Click "Select Kernel" (top-right)
3. Choose "DARA MP Tutorial" or your environment
4. Run cells with Shift+Enter

---

## Troubleshooting

### Issue: Import Error for `dara_adapter`
**Solution**: Ensure `scripts/` is in your path:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd().parent / 'scripts'))
```

### Issue: Index files not found
**Solution**: Check paths in the notebook:
```python
# Update these paths if needed
icsd_index_path = Path.cwd().parent / 'indexes' / 'icsd_index_filled.parquet'
mp_index_path = Path.cwd().parent / 'indexes' / 'mp_index.parquet'
```

### Issue: UV not installing packages
**Solution**: Use verbose mode to see errors:
```powershell
uv pip install -e ".[docs]" --verbose
```

### Issue: Jupyter kernel not showing
**Solution**: Restart Jupyter and refresh kernels:
```powershell
jupyter kernelspec list  # See installed kernels
jupyter notebook  # Restart Jupyter
```

### Issue: Ray initialization errors (Windows)
**Solution**: Ray might have issues on Windows. If you see Ray errors, you can disable parallelization in DARA by setting `n_jobs=1` in search functions.

---

## Performance Notes

### Memory Requirements
- **Minimum**: 8 GB RAM
- **Recommended**: 16 GB+ RAM
- **Optimal**: 32 GB+ RAM (for large-scale phase search)

### Storage Requirements
- **Indices**: ~100 MB (parquet files)
- **CIF files**: 
  - ICSD: ~10 GB
  - COD: ~102 GB (optional, can download on-demand)
  - MP: ~2 GB
- **Total**: ~115 GB (with all CIF files)

### Speed Optimization
- Use SSD for CIF storage
- Limit `max_phases` parameter to reduce search time
- Use parallel processing where available (except on Windows with Ray issues)

---

## Package Versions (Tested)

```
Python: 3.11.13
dara-xrd: 1.1.1
pymatgen: 2025.5.1
pandas: 2.2.0
pyarrow: 15.0.0
plotly: 5.18.0
jupyter: 1.0.0
ipywidgets: 8.1.3
nbformat: 5.9.2
```

---

## Additional Resources

- **DARA Documentation**: https://idocx.github.io/dara/
- **Scripts README**: `scripts/README.md`
- **CHANGELOG**: `CHANGELOG.md`
- **MP Integration**: `RELEASE_v3.0.md`

---

**Last Updated**: October 29, 2025  
**Environment Version**: 3.0 (MP Integration)
