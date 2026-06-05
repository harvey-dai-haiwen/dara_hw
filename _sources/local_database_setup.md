# Local Database Setup

This guide describes how to prepare local crystallographic mirrors for Dara
search-match runs on the accelerate branch. The preferred handoff model is a
separate database-entry repository called `CIF_index`, checked out locally as
`D:\Haiwen\Databases\Structure_index` on this workstation. The mirrors
themselves are private data and must not be committed.

For from-zero setup, use the canonical deployment script first:

```powershell
git lfs install
python scripts/setup_local_dara.py --clone-cif-index --build-mp-index
uv run python scripts/validate_local_setup.py --run-pytest --run-smoke
```

To debug database links and permissions without downloading the full COD archive
or MP pickle:

```powershell
uv run python scripts/check_database_sources.py
```

This page documents the database layout expected by that script and by Dara.

## Runtime Contract

Dara's database layer expects local CIF mirrors plus small metadata indexes:

```text
Structure_index/
  cod_cifs/        # optional local COD mirror
  icsd_cifs/       # optional local ICSD mirror, license required
  mp_cifs/         # optional local Materials Project CIF mirror
  indexes/         # optional fast parquet indexes, mainly used by MP
```

The default package paths are defined in `src/dara/settings.py`, but team
machines should prefer a `~/.dara.yaml` pointing to the standalone
`Structure_index` checkout:

```yaml
PATH_TO_STRUCTURE_INDEX: D:/Haiwen/Databases/Structure_index
```

When `PATH_TO_STRUCTURE_INDEX` is set, Dara derives these local mirrors unless
you explicitly override them:

```text
PATH_TO_COD  = <PATH_TO_STRUCTURE_INDEX>/cod_cifs
PATH_TO_ICSD = <PATH_TO_STRUCTURE_INDEX>/icsd_cifs
PATH_TO_MP   = <PATH_TO_STRUCTURE_INDEX>/mp_cifs
```

You can also keep the explicit paths in `~/.dara.yaml` for older Dara checkouts:

```yaml
PATH_TO_COD: D:/Haiwen/Databases/Structure_index/cod_cifs
PATH_TO_ICSD: D:/Haiwen/Databases/Structure_index/icsd_cifs
PATH_TO_MP: D:/Haiwen/Databases/Structure_index/mp_cifs
```

Environment variables also work because settings use the `dara_` prefix:

```powershell
$env:dara_PATH_TO_STRUCTURE_INDEX = "D:\Haiwen\Databases\Structure_index"
$env:dara_PATH_TO_COD = "D:\Haiwen\Databases\Structure_index\cod_cifs"
$env:dara_PATH_TO_ICSD = "D:\Haiwen\Databases\Structure_index\icsd_cifs"
$env:dara_PATH_TO_MP = "D:\Haiwen\Databases\Structure_index\mp_cifs"
```

## COD

COD is public. To create a local mirror:

```bash
rsync -av --delete rsync://www.crystallography.net/cif/ COD_2024/
```

Then either move or point Dara to the mirror:

```text
cod_cifs/
  1/00/00/1000000.cif
  1/00/00/1000001.cif
  ...
```

Dara accepts both `cod_cifs/` and `cod_cifs/cif/` layouts.

The tracked COD metadata file used for chemical-system lookup is:

```text
src/dara/data/cod_filtered_info_2024.json.gz
```

If the COD mirror changes substantially, rebuild this metadata from the local
mirror:

```powershell
uv run python scripts/filter_cod.py
```

The script writes `cod_filtered_info_2024.json.gz` in the current working
directory. Review it, then replace `src/dara/data/cod_filtered_info_2024.json.gz`
only if you intentionally want a new metadata snapshot.

## ICSD

ICSD requires a paid license. Dara does not provide ICSD CIFs and does not
download them. Use only a local copy permitted by your ICSD agreement.

Supported layouts:

```text
icsd_cifs/
  icsd_123456.cif
  icsd_123457.cif
```

or sharded numeric files:

```text
icsd_cifs/
  cif/
    0/03/87/38768.cif
```

Dara resolves both layouts during search-match. The tracked ICSD metadata file
used for chemical-system lookup is:

```text
src/dara/data/icsd_filtered_info_2025_v3.json.gz
```

If you intentionally rebuild the ICSD metadata snapshot, use:

```powershell
uv run python scripts/filter_icsd.py
```

Important: `scripts/filter_icsd.py` currently expects flat `icsd_*.cif` input.
If your local ICSD mirror is sharded, either use the existing tracked metadata
snapshot or create a temporary flat export before rebuilding the metadata file.

## Materials Project

Materials Project CIF downloading is not implemented in Dara. Prepare a local
CIF mirror from your own permitted MP export.

The preferred local layout is sharded by the database id:

```text
mp_cifs/
  0/00/mp-9.cif
  0/00/mp-90.cif
  1/10/mp-1026684.cif
  m/mv/mvc-11882.cif
```

Dara's `MPDatabase.get_file_path()` uses this routing. For direct local-folder
searches you can also use `--no-database --additional-cif-dir`, but for
`--database MP` the mirror should follow the sharded MP layout above.

MP uses:

```text
src/dara/data/mp_struct_info.json.gz
<PATH_TO_STRUCTURE_INDEX>/indexes/mp_index.jsonl.gz
<PATH_TO_STRUCTURE_INDEX>/indexes/mp_index.parquet
```

At runtime, Dara first tries
`<PATH_TO_STRUCTURE_INDEX>/indexes/mp_index.jsonl.gz`, then
`<PATH_TO_STRUCTURE_INDEX>/indexes/mp_index.parquet` if `pyarrow` is installed,
then falls back to the legacy repo-local `indexes/mp_index.parquet`. If no
durable index is present, Dara scans `mp_cifs/**/*.cif` and builds the
chemical-system index in memory. That fallback is convenient but can be slow on a
full MP mirror.

Both JSONL and parquet rows use this schema:

```text
raw_db_id
formula
elements
spacegroup
energy_above_hull
```

To build the portable JSONL index from the local MP-in-ICSD pickle:

```text
python scripts/setup_local_dara.py --build-mp-index
```

After `CIF_index` is cloned with Git LFS enabled, the setup script automatically
uses `<PATH_TO_STRUCTURE_INDEX>/indexes/df_MPinICSD_20250211_withstructure.pkl`.
Pass `--mp-pickle PATH` only when the pickle lives elsewhere.

## Validation

After configuring mirrors, run focused database tests:

```powershell
uv run pytest
```

Then run a dry-run through the unified search-match entrypoint:

```powershell
uv run python -m dara.search_match_cli `
  --xrd tests/test_data/BiFeO3.xy `
  --output-root .tmp/db-dry-run `
  --database ICSD `
  --must-element Bi --must-element Fe --possible-element O `
  --logical-threads 4 --memory-gb 16 --cpu-target-fraction 0.5 `
  --dry-run
```

For a local-CIF-only validation that does not touch ICSD/COD/MP mirrors:

```powershell
uv run python -m dara.search_match_cli `
  --xrd tests/test_data/BiFeO3.xy `
  --output-root .tmp/local-cif-dry-run `
  --no-database `
  --additional-cif-dir tests/test_data `
  --must-element Bi --must-element Fe --possible-element O `
  --logical-threads 4 --memory-gb 16 --cpu-target-fraction 0.5 `
  --dry-run
```

The dry-run should write:

```text
<output-root>/summary.json
<output-root>/candidates/selected/*.cif
```

## Publication Hygiene

Do not commit local mirrors, rebuilt private metadata, scratch outputs, or
machine-specific indexes unless the team explicitly agrees that the file is
public and reproducible. ICSD CIFs must never be published from Dara or from
`CIF_index`.
