# UV Environment Setup Guide

This guide ensures a one-time setup of all dependencies for the `dara-xrd` package using UV.

## Quick Start

```bash
# 1. Install UV (if not already installed)
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone the repository
git clone <your-repo-url>
cd dara

# 3. Sync all dependencies (one command does it all!)
uv sync

# 4. Verify installation
uv run python verify_dependencies.py
```

## What Gets Installed

The UV environment includes **all** dependencies needed for `dara-xrd`:

### Core Dependencies (60+ packages)
- **Scientific Computing**: numpy, pandas, scipy, scikit-learn
- **Crystallography**: pymatgen>=2025.1.1, spglib>=2.5.0
- **Data Handling**: pyarrow>=22.0.0 (parquet files)
- **Visualization**: plotly>=5.3.1
- **Parallel Processing**: ray>=2.48.0
- **Web Framework**: fastapi>=0.115.6, uvicorn>=0.34.0
- **Materials Data**: mp_api>=0.45.0, reaction-network>=8.3.0
- **And many more...**

See `pyproject.toml` for the complete list.

### Optional Dependencies

```bash
# Install test dependencies
uv sync --extra tests

# Install documentation dependencies
uv sync --extra docs

# Install strict versions (pinned)
uv sync --extra strict

# Install all extras
uv sync --all-extras
```

## Using the Environment

### Run Python scripts
```bash
uv run python your_script.py
```

### Run Jupyter notebooks
```bash
uv run jupyter notebook
```

### Run tests
```bash
uv run pytest
```

### Import in Python
```bash
uv run python -c "import dara; print(dara.__version__)"
# Output: 1.1.2+hw
```

## Verification

After installation, verify all dependencies:

```bash
uv run python verify_dependencies.py
```

Expected output:
```
======================================================================
DARA-XRD Dependency Verification
======================================================================
...
✅ All critical dependencies are available!
```

## Troubleshooting

### Issue: File lock error during `uv sync`
**Solution**: Close all Python processes, IDEs, and terminals using the environment, then retry.

```bash
# Windows: Kill Python processes
taskkill /F /IM python.exe

# Then retry
uv sync
```

### Issue: Import errors after installation
**Solution**: Resync the environment

```bash
uv sync --reinstall
```

### Issue: Wrong Python version
**Solution**: UV will automatically download the correct Python version (3.10+)

```bash
# Check Python version in UV environment
uv run python --version
```

## Key Files

- **`pyproject.toml`**: Package configuration and dependency specification
- **`uv.lock`**: Locked dependency versions for reproducibility
- **`verify_dependencies.py`**: Dependency verification script

## Version Information

- **Package**: `dara-xrd==1.1.2+hw`
- **Python**: >=3.10 (tested on 3.10, 3.11, 3.12, 3.13)
- **UV**: >=0.5.0

## Changes from Original DARA

This fork (`dara-xrd==1.1.2+hw`) includes:

1. ✅ **UV support**: One-command environment setup
2. ✅ **PEP 440 compliance**: Version format `1.1.2+hw`
3. ✅ **pyarrow dependency**: Explicitly declared for parquet support
4. ✅ **Chemical system filtering**: Subset-based phase filtering
5. ✅ **Improved notebooks**: Streamlined phase analysis workflows

## Migration from Conda/Pip

If you're migrating from conda or pip:

```bash
# 1. Deactivate existing environment
conda deactivate  # or deactivate virtualenv

# 2. Clean up old environments (optional)
rm -rf .venv .venv_dara

# 3. Set up UV environment
uv sync

# 4. Verify
uv run python verify_dependencies.py
```

## CI/CD Integration

For automated testing:

```yaml
# .github/workflows/test.yml
- name: Set up UV
  run: curl -LsSf https://astral.sh/uv/install.sh | sh

- name: Install dependencies
  run: uv sync --all-extras

- name: Run tests
  run: uv run pytest
```

## Additional Resources

- UV Documentation: https://docs.astral.sh/uv/
- DARA Documentation: https://idocx.github.io/dara/
- pyproject.toml spec: https://packaging.python.org/en/latest/specifications/pyproject-toml/
