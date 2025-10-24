Build candidate CIF index
=========================

This folder contains helper scripts to build a filtered CIF index for use with DARA.

Primary script
--------------
- `build_candidate_index.py` — Build a gzipped JSON index from ICSD CSV, Materials Project pickle, and a COD CIF directory. It supports filtering by required/optional elements, density, and number of sites, and can copy filtered CIF files to a folder for DARA to consume as `additional_phases`.

Usage examples
--------------

Create an index using ICSD CSV, MP pickle and COD folder, require Li and O, optionally Fe, and export CIFs:

```powershell
python .\scripts\build_candidate_index.py --use-icsd --icsd-csv "C:\path\to\[Kedar_Group_ONLY]_ICSD2024_summary_2024.2_v5.3.0.csv" \
  --use-mp --mp-pkl "C:\path\to\df_MP_20250211.pkl" \
  --use-cod --cod-dir "C:\path\to\cod_cifs_extracted" \
  --required-elements Li,O --optional-elements Fe \
  --export-cif-dir .\filtered_cifs --out-index .\filtered_index.json.gz
```

Notes
-----
- The script intentionally does not modify existing source files in the repository.
- For large COD or MP datasets, indexing may take a long time and require memory; consider running on a machine with sufficient resources.
# Scripts

**mp_struct_info.json.gz**: This data file contains the formula, spacegroup, and
approximate e_hull for all entries on the Materials Project. This is required to run the
filter_icsd.py and filter_cod.py scripts.
