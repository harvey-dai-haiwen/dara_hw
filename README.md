![DARA logo](https://github.com/CederGroupHub/dara/blob/main/logo/dara.jpg?raw=true)

# DARA: Data-driven automated Rietveld analysis for phase search and refinement
[![GitHub licence](https://img.shields.io/github/license/CederGroupHub/dara)](https://github.com/CederGroupHub/dara/blob/main/LICENSE)
[![DOI](https://img.shields.io/badge/DOI-10.1021%2Facs.chemmater.5c02820-blue)](https://doi.org/10.1021/acs.chemmater.5c02820)
[![Pytest](https://github.com/CederGroupHub/dara/actions/workflows/pytest.yaml/badge.svg?branch=main)](https://github.com/CederGroupHub/dara/actions/workflows/pytest.yaml)
[![Ruff Check](https://github.com/CederGroupHub/dara/actions/workflows/ruff.yaml/badge.svg?branch=main)](https://github.com/CederGroupHub/dara/actions/workflows/ruff.yaml)

Automated phase search with BGMN.

## Installation

```bash
pip install dara-xrd
```

For pip-style local installs without `uv`, use the exported requirement files:

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pip install -r requirements-tests.txt
```

For more details about installation, please refer to [installation guide](https://CederGroupHub.github.io/dara/install.html).

## Local development

This repository is maintained with `uv` for local development. The recommended workflow is:

```bash
uv python install 3.11
uv sync --extra tests
uv run pytest tests/test_structure_db.py tests/test_api_router.py
```

The repository only needs the `uv`-managed `.venv` for development. Extra local environments such as Conda or ad hoc virtual environments are not required.

The release surfaces are:

- `pyproject.toml` for package builds and extras
- `requirements.txt` for base runtime installs
- `requirements-tests.txt` for local validation installs

If you maintain local crystallographic mirrors for search-match workflows, see
the repo guide at `docs/local_database_setup.md` and the recovery notes in the
documentation: https://cedergrouphub.github.io/dara/local_database_recovery.html

## Local custom-sample benchmarking

For real-sample benchmarking from a local checkout, use `scripts/benchmark_custom_sample.py`. This runner preserves Dara's original maker and jobflow path and writes all outputs into repository-local `custom-test-samples/` folders.

Example, COD search on a Y-Mo-O sample:

```bash
uv run python scripts/benchmark_custom_sample.py --sample-path D:\XRD_Analysis\DTMA_YMoO3\20231212_YCl3Onepot_1200.xy --database cod --precursor Y2O3 --precursor MoO3
```

Switch to ICSD by changing `--database icsd`.

Expected outputs under `custom-test-samples/<sample-slug>/<database>/` include:

- `summary.json`
- HTML refinement plots for retained candidates
- grouped phase summaries and serialized benchmark outputs

At the sample root, Dara also writes `custom-test-samples/<sample-slug>/benchmark_summary.json`.

Operational notes:

- COD, ICSD, MP, and combined runs should be launched as separate benchmark jobs when you want comparable timings
- on Windows, do not overlap reruns that target the same sample and database output directory
- this path expects local crystallographic mirrors to be available in the checkout

## Programmatic Search-Match Workflow

The accelerate branch exposes one resource-aware workflow for scripts, CLIs, and agent skills:

- Python API: `dara.run_search_match(config)`
- CLI: `dara-search-match`
- Outputs: `<output-root>/summary.json` plus per-rank files under `<output-root>/searchmatch/rank_###/`

The workflow accepts one XRD pattern, local database selection (`ICSD`, `COD`, `MP`), the built-in three-group element filter, optional user CIF files/directories, optional external CSVs containing CIF text, and refinement/backend resource settings. It then runs Dara search-match and exports ranked refinement plots and phase fractions.

Element filtering is intentionally strict:

- `must`: every selected CIF must contain all elements in this group.
- `any`: selected CIF must contain at least one listed element.
- `any-expression`: boolean expression such as `Na|(Cl&Mo)`.
- `possible`: allowed but not required elements.
- No other elements are allowed, and one element may appear in only one group.

CLI example using only local folder CIFs:

```bash
dara-search-match --xrd D:\sample\pattern.xy ^
  --no-database ^
  --additional-cif-dir D:\sample\cifs ^
  --any-element Ni --any-element Sn --any-element Se ^
  --possible-element C --possible-element O ^
  --physical-cores 16 --logical-threads 32 --memory-gb 128 ^
  --cpu-target-fraction 0.40 --bgmn-threads 4 --max-parallel-jobs 3 ^
  --instrument-profile monochromated_xrd ^
  --output-root D:\sample\metadata\dara\local-cif-search
```

CLI example using ICSD plus an external CSV with CIF text:

```bash
dara-search-match --xrd D:\sample\pattern.xy ^
  --database ICSD ^
  --any-element Ni --any-element Sn --any-element Se ^
  --possible-element C --possible-element O ^
  --external-csv D:\sample\wf_tnmtps_am20_kgb2.2_Ni-Se-Sn.csv ^
  --physical-cores 16 --logical-threads 32 --memory-gb 128 ^
  --cpu-target-fraction 0.40
```

Python example:

```python
from pathlib import Path

from dara import (
    DaraSearchMatchConfig,
    ElementFilterConfig,
    MachineConfig,
    run_search_match,
)

summary = run_search_match(
    DaraSearchMatchConfig(
        sample_path=Path(r"D:\sample\pattern.xy"),
        output_root=Path(r"D:\sample\metadata\dara\run001"),
        databases=("ICSD",),
        element_filter=ElementFilterConfig(any=("Ni", "Sn", "Se"), possible=("C", "O")),
        additional_cif_dirs=(Path(r"D:\sample\extra_cifs"),),
        instrument_profile="monochromated_xrd",
        machine=MachineConfig(
            physical_cores=16,
            logical_threads=32,
            memory_gb=128,
            cpu_target_fraction=0.40,
            bgmn_threads=4,
            max_parallel_jobs=3,
        ),
    )
)
print(summary["best_rwp"], summary["output_root"])
```

Expected output files:

- `summary.json`: full machine settings, candidate counts, filter decisions, result ranks, and warnings.
- `searchmatch/rank_###/refinement_plot.html`: interactive observed/calculated/residual refinement plot.
- `searchmatch/rank_###/phase_fractions.csv` and `.json`: refined phase fractions.
- `searchmatch/rank_###/refinement_summary.json`: R factors and phase metadata for that rank.

## Release smoke checklist

For a handoff-ready local checkout, validate these in order:

1. `uv sync --extra tests`
2. `uv run pytest tests/test_structure_db.py tests/test_api_router.py`
3. `uv run python scripts/benchmark_custom_sample.py --sample-path <path-to-pattern.xy> --database cod --precursor <formula> --precursor <formula>`
4. `uv build`

## Web Server
Dara ships with a browser-based web server for an out-of-box experience of Dara. To launch the webserver, run
```bash
dara server
```

Then you can open http://localhost:8898 to see an application that can submit, manage, and view jobs.


## Documentation
For more details about usage, please refer to the [documentation](https://CederGroupHub.github.io/dara/).

## Citation
If you use DARA in your research, please consider citing the following paper:

```
@article{doi:10.1021/acs.chemmater.5c02820,
  author = {Fei, Yuxing and McDermott, Matthew J. and Rom, Christopher L. and Wang, Shilong and Ceder, Gerbrand},
  title = {Dara: Automated Multiple-Hypothesis Phase Identification and Refinement from Powder X-ray Diffraction},
  journal = {Chemistry of Materials},
  volume = {38},
  number = {3},
  pages = {1364-1376},
  year = {2026},
  doi = {10.1021/acs.chemmater.5c02820},
  url = {https://doi.org/10.1021/acs.chemmater.5c02820},
  eprint = {https://doi.org/10.1021/acs.chemmater.5c02820}
}
```
