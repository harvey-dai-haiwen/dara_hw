# Local Database Recovery

This note describes the expected local mirror layout for Dara search-match development and
how to recover the mirrors if they need to be rebuilt.

## What should exist locally

For local development, the repository may keep private crystallographic mirrors outside of
version control. The current Dara integration expects these working directories:

- `cod_cifs/`
- `icsd_cifs/`
- `mp_cifs/`
- `indexes/`

These directories are intentionally ignored by Git and should not be published with the
repository.

## Preferred runtime

Use the repository-local `uv` environment for validation and repair tasks:

```bash
uv python install 3.11
uv sync --extra tests
```

## Before rebuilding anything

If the local mirrors already exist, validate them before attempting a rebuild. The current
integration supports a few different on-disk layouts, so a path mismatch does not
necessarily mean the mirror is damaged.

Run the focused checks first:

```bash
uv run pytest
```

## Source datasets used for recovery

If a mirror is genuinely missing or corrupted, rebuild it from the original local sources:

- MP: `df_MP_20250211`
- ICSD: `[Kedar_Group_ONLY]_ICSD2024_summary_2024.2_v5.3.0_DOI_update`
- COD: `cod-cifs-mysql`

## Database-specific notes

### COD

The local COD mirror may live directly under `cod_cifs/` or under a nested `cif/` folder.
The Dara structure database layer now normalizes either layout.

### ICSD

The local ICSD mirror can be stored in either of these forms:

- flat files such as `icsd_<id>.cif`
- sharded numeric files such as `icsd_cifs/cif/0/03/87/38768.cif`

The current local mirror uses the sharded numeric layout. Dara now resolves both layouts,
so there is no need to rename a healthy ICSD mirror just to satisfy the search layer.

### MP

The Materials Project metadata file in `src/dara/data/mp_struct_info.json.gz` does not carry
the full local CIF placement information. Dara derives MP IDs from the local `mp_cifs/`
tree, so the local CIF mirror must remain consistent with the metadata snapshot.

## Recovery checklist

1. Restore or rebuild the raw local CIF mirrors from the original source datasets.
2. Confirm the root directories referenced by Dara settings point to the recovered mirrors.
3. Recreate the local environment with `uv sync --extra tests` if needed.
4. Run `uv run pytest`.
5. Run a real search-match validation against the database you repaired before trusting the mirror for broader `ALL` searches.

## Publication hygiene

Local mirrors, indexes, worker state, and scratch diagnostics are for development only.
Keep them ignored or remove them before publication so that the tracked patch contains only
source, tests, and documentation.
