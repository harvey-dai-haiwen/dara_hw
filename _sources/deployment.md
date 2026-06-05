# Local Deployment Guide

This guide is the canonical handoff path for a local Dara checkout. It is written
for both human users and coding agents. The default runtime is the repository
local `uv` virtual environment; Conda is not required for normal Dara, BGMN, or
search-match workflows.

## Clean Repository Policy

The Dara git repository tracks source code, tests, package data, and small test
fixtures only. Do not commit local XRD patterns, search-match outputs, Rietveld
plots, copied database CIFs, jobflow working folders, or benchmark result
folders.

Ignored local artifacts include:

- `custom-test-samples/`
- `.tmp/`
- `metadata/`
- `searchmatch/`
- BGMN/GSAS-II/FullProf output files such as `.lst`, `.dia`, `.par`, `.gpx`,
  `.pcr`, `.prf`, `.sum`, and `.out`
- local XRD files such as `.xy`, `.xye`, `.rasx`, `.raw`, and `.brml`

The small files under `tests/test_data/` are intentionally tracked as fixtures.

## From Zero: Environment

Install `uv`, clone the repo, then run:

```powershell
git clone https://github.com/harvey-dai-haiwen/dara_hw.git dara
cd dara
git checkout dara-accelerate
python scripts/setup_local_dara.py --skip-uv-sync
uv sync --extra tests
uv run python scripts/validate_local_setup.py --run-pytest --run-smoke
```

If `uv` is already installed and you want the setup script to run dependency
sync for you:

```powershell
python scripts/setup_local_dara.py
uv run python scripts/validate_local_setup.py --run-pytest --run-smoke
```

The expected Python for all local work is:

```text
<repo>/.venv/Scripts/python.exe
```

Use `uv run ...` for commands:

```powershell
uv run pytest
uv run dara-search-match --help
uv run dara server
```

## Database Root

Dara uses a separate local database-entry repository called `CIF_index` or
`Structure_index`. On this workstation the default path is:

```text
D:/Haiwen/Databases/Structure_index
```

The expected layout is:

```text
Structure_index/
  cod_cifs/        # local COD mirror, ignored by git
  icsd_cifs/       # licensed ICSD mirror, ignored by git
  mp_cifs/         # local MP CIF mirror, ignored by git
  indexes/         # shareable metadata/index files
```

`CIF_index` is a private GitHub repository. A new user or agent must have GitHub
access to `harvey-dai-haiwen/CIF_index`; without access, GitHub may report
`Repository not found` even when the URL is correct. Git LFS is also required
because the MP pickle and SQLite indexes are stored as LFS objects.

Check links and permissions without downloading full databases:

```powershell
git lfs install
uv run python scripts/check_database_sources.py
```

The check performs:

- `git ls-remote` against the private `CIF_index` repository
- a temporary `GIT_LFS_SKIP_SMUDGE=1` clone to verify LFS pointers
- an HTTP HEAD request for the public COD archive
- local `Structure_index` inspection

Fresh private-index checkout:

```powershell
git lfs install
python scripts/setup_local_dara.py `
  --structure-index D:\Haiwen\Databases\Structure_index `
  --clone-cif-index `
  --build-mp-index
```

Use `--skip-cif-index-lfs` only for link/debug tests; it leaves the large MP
pickle as a pointer file and cannot build the MP JSONL index until `git lfs
pull` is run.

The setup script writes `~/.dara.yaml`:

```yaml
PATH_TO_STRUCTURE_INDEX: D:/Haiwen/Databases/Structure_index
PATH_TO_COD: D:/Haiwen/Databases/Structure_index/cod_cifs
PATH_TO_ICSD: D:/Haiwen/Databases/Structure_index/icsd_cifs
PATH_TO_MP: D:/Haiwen/Databases/Structure_index/mp_cifs
```

You can override the path:

```powershell
python scripts/setup_local_dara.py --structure-index D:\Databases\Structure_index
```

For non-interactive agent setup:

```powershell
python scripts/setup_local_dara.py `
  --structure-index D:\Databases\Structure_index `
  --non-interactive
```

## COD

Best path: provide a local COD CIF mirror in:

```text
<Structure_index>/cod_cifs/
```

If no local mirror is available, the setup script can download the public COD
archive from:

```text
http://www.crystallography.net/archives/cod-cifs-mysql.txz
```

Interactive mode asks before downloading. Non-interactive mode requires an
explicit flag:

```powershell
python scripts/setup_local_dara.py --download-cod
```

The COD archive is about 17 GB. For setup debugging, use
`scripts/check_database_sources.py` instead of `--download-cod`.

If the archive is already available locally:

```powershell
python scripts/setup_local_dara.py --cod-archive D:\Haiwen\Databases\cod-cifs-mysql.txz
```

COD CIFs remain local-only and are not committed.

## ICSD

ICSD is licensed data. Dara does not download or distribute ICSD CIFs. Put a
permitted local ICSD mirror under:

```text
<Structure_index>/icsd_cifs/
```

Supported layouts:

```text
icsd_cifs/icsd_123456.cif
icsd_cifs/cif/0/03/87/38768.cif
```

ICSD CIFs must never be committed.

## Materials Project

Best path: provide a local MP CIF mirror under:

```text
<Structure_index>/mp_cifs/
```

The preferred sharded layout is:

```text
mp_cifs/0/00/mp-9.cif
mp_cifs/1/10/mp-1026684.cif
mp_cifs/m/mv/mvc-11882.cif
```

For metadata indexing, this workstation has:

```text
D:/Haiwen/Databases/df_MPinICSD_20250211_withstructure.pkl
```

The setup script can build a portable JSONL index that Dara can read without
`pyarrow`:

```powershell
python scripts/setup_local_dara.py `
  --build-mp-index
```

This writes:

```text
<Structure_index>/indexes/mp_index.jsonl.gz
```

When `CIF_index` has been cloned with LFS enabled, the setup script automatically
uses:

```text
<Structure_index>/indexes/df_MPinICSD_20250211_withstructure.pkl
```

You only need `--mp-pickle PATH` when the pickle is stored somewhere else.

If the team wants to publish the large MP pickle inside the private `CIF_index`
repo, copy it into the index repo and track it with Git LFS:

```powershell
python scripts/setup_local_dara.py `
  --mp-pickle D:\Haiwen\Databases\df_MPinICSD_20250211_withstructure.pkl `
  --copy-mp-pickle
```

Raw MP CIFs remain local-only and are not committed.

## Validation

Fast validation:

```powershell
uv run python scripts/validate_local_setup.py
```

Full validation:

```powershell
uv run python scripts/validate_local_setup.py --run-pytest --run-smoke
```

Database dry run with local CIF fixtures only:

```powershell
uv run dara-search-match `
  --xrd tests\test_data\BiFeO3.xy `
  --output-root .tmp\local-cif-dry-run `
  --no-database `
  --additional-cif-dir tests\test_data `
  --must-element Bi --must-element Fe --possible-element O `
  --logical-threads 4 --memory-gb 16 --cpu-target-fraction 0.5 `
  --dry-run
```

Actual BGMN smoke:

```powershell
uv run dara-search-match `
  --xrd tests\test_data\BiFeO3.xy `
  --output-root .tmp\local-cif-bgmn-smoke `
  --no-database `
  --additional-cif tests\test_data\BiFeO3.cif `
  --must-element Bi --must-element Fe --possible-element O `
  --logical-threads 4 --memory-gb 16 --cpu-target-fraction 0.5 `
  --max-phases 1 --max-results 1 `
  --bgmn-threads 1 --max-parallel-jobs 1 `
  --backend-timeout 180
```

## Optional Backends

BGMN is the default backend and is bundled for local Dara workflows.

GSAS-II and FullProf are optional confirmation backends:

- GSAS-II requires an external GSAS-II installation or environment.
- FullProf requires `fp2k.exe`.

These optional backends are not required for the default `uv` setup.
