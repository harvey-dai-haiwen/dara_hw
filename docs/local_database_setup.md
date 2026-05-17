# Local Database Setup

This guide describes how to prepare local crystallographic mirrors for Dara
search-match runs on the accelerate branch. The mirrors themselves are private
data and must not be committed.

## Runtime Contract

Dara's database layer expects local CIF mirrors plus small metadata indexes:

```text
dara/
  cod_cifs/        # optional local COD mirror
  icsd_cifs/       # optional local ICSD mirror, license required
  mp_cifs/         # optional local Materials Project CIF mirror
  indexes/         # optional fast parquet indexes, mainly used by MP
```

The default paths are defined in `src/dara/settings.py`:

```text
PATH_TO_COD  = ~/COD_2024
PATH_TO_ICSD = ~/ICSD_2024/ICSD_2024_experimental_inorganic/experimental_inorganic
PATH_TO_MP   = ~/mp_cifs
```

For a repo-local checkout, either pass database objects with explicit paths from
Python, or create `~/.dara.yaml`:

```yaml
PATH_TO_COD: D:/Haiwen/Code_Repositories/dara/cod_cifs
PATH_TO_ICSD: D:/Haiwen/Code_Repositories/dara/icsd_cifs
PATH_TO_MP: D:/Haiwen/Code_Repositories/dara/mp_cifs
```

Environment variables also work because settings use the `dara_` prefix:

```powershell
$env:dara_PATH_TO_COD = "D:\Haiwen\Code_Repositories\dara\cod_cifs"
$env:dara_PATH_TO_ICSD = "D:\Haiwen\Code_Repositories\dara\icsd_cifs"
$env:dara_PATH_TO_MP = "D:\Haiwen\Code_Repositories\dara\mp_cifs"
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
indexes/mp_index.parquet
```

At runtime, Dara first tries `indexes/mp_index.parquet` if `pyarrow` is
installed. The parquet schema must contain:

```text
raw_db_id
formula
elements
spacegroup
energy_above_hull
```

If `indexes/mp_index.parquet` is missing, Dara scans `mp_cifs/**/*.cif` and
builds the chemical-system index in memory. That fallback is convenient but can
be slow on a full MP mirror.

There is no formal MP index-builder CLI in the repo yet. If you need a durable
parquet index, generate it from your local CIF export with those five columns
and write it to:

```text
indexes/mp_index.parquet
```

## Validation

After configuring mirrors, run focused database tests:

```powershell
uv run pytest tests/test_structure_db.py tests/test_api_router.py
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
public and reproducible. ICSD CIFs must never be published from this repository.
