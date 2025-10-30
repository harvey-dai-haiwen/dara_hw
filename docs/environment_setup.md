# Environment Setup with UV

This guide walks through creating a reproducible development environment for Dara 3.0 using the fast **uv** package manager. The steps cover everything required to run the core library, the streamlined phase analysis notebook, and the supporting database utilities.

---

## 1. Prerequisites

- **Operating system:** Windows, macOS, or Linux (64-bit)
- **Python:** 3.11 (recommended) or any supported version in the `pyproject.toml`
- **Build tools:**
  - Windows: Visual C++ Build Tools (via the Build Tools for Visual Studio installer)
  - macOS: Xcode Command Line Tools (`xcode-select --install`)
  - Linux: `build-essential`, `libffi-dev`, `libopenblas-dev`, and `liblapack-dev`
- **Internet access** to download dependencies and database archives

---

## 2. Install uv (one time)

```powershell
# Windows PowerShell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installation, restart the shell so that `uv` is available on your PATH.

---

## 3. Clone Dara and bootstrap the environment

```powershell
# Pick a location for the source code
cd C:\Users\<you>\Documents

# Clone the repository
git clone https://github.com/idocx/dara.git
cd dara

# Create the virtual environment inside the repo
uv venv .venv --python 3.11

# Activate (PowerShell)
.\.venv\Scripts\Activate.ps1

# On macOS/Linux use:
# source .venv/bin/activate
```

---

## 4. Install Dara with all runtime extras

```powershell
# Install Dara in editable mode with doc + web extras
uv pip install -e ".[docs]"

# Install notebook utilities used by streamlined_phase_analysis.ipynb
uv pip install jupyterlab ipykernel nbformat ipywidgets

# Optional: install test tools
uv pip install -e ".[tests]"
```

### Register a dedicated Jupyter kernel

```powershell
python -m ipykernel install --user --name=dara-uv --display-name="Dara (uv)"
```

---

## 5. Verify the installation

```powershell
python - <<'PY'
import dara
import pymatgen
import plotly
import pandas as pd
print("✅ Dara version:", dara.__version__)
print("✅ Pymatgen version:", pymatgen.__version__)
PY
```

You should see version numbers without import errors.

---

## 6. Optional: Install BGMN binaries

Dara ships with the BGMN executables in `src/dara/bgmn`. No extra steps are required on Windows or macOS. On Linux clusters with older GLIBC versions, follow the detailed instructions in `docs/install.md` to patch-in the provided binaries.

---

## 7. Launch the streamlined workflow notebook

```powershell
# Make sure the environment is active
.\.venv\Scripts\Activate.ps1

# Start Jupyter Lab
jupyter lab
```

Open `notebooks/streamlined_phase_analysis.ipynb`, select the **Dara (uv)** kernel, and run the cells in order. The notebook expects the indexed databases described in `docs/database_update.md` to be present.

---

## 8. Keeping dependencies up to date

```powershell
# Update uv itself
uv self update

# Update project dependencies while staying inside the venv
uv pip install -e "." --upgrade
```

For repeatable deployments, check `pyproject.toml` into version control and pin any additional packages inside the optional groups.

---

## 9. Troubleshooting tips

| Problem | Fix |
|---------|-----|
| `ImportError: DLL load failed` on Windows | Ensure Visual C++ Build Tools are installed and restart the shell |
| `ModuleNotFoundError: pymatgen` | Re-run `uv pip install -e ".[docs]"` to install all extras |
| Jupyter kernel not listed | Run `python -m ipykernel install --user --name=dara-uv --display-name="Dara (uv)"` again |
| Ray startup errors on Windows | Pass `n_jobs=1` to DARA search functions to disable Ray or install WSL2 |

---

**Last updated:** October 30, 2025
