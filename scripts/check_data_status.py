from pathlib import Path
import sys

try:
    import pandas as pd
except Exception as e:
    print("pandas not installed. Run: uv pip install pandas pyarrow", file=sys.stderr)
    sys.exit(1)

REPO = Path(__file__).resolve().parents[1]
IDX = REPO / 'indexes'
COD = REPO / 'cod_cifs'
ICSD = REPO / 'icsd_cifs'
MP = REPO / 'mp_cifs'

FILES = {
    'icsd_index_filled.parquet': IDX / 'icsd_index_filled.parquet',
    'cod_index_filled.parquet': IDX / 'cod_index_filled.parquet',
    'mp_index.parquet': IDX / 'mp_index.parquet',
    'merged_index.parquet': IDX / 'merged_index.parquet',
}

DIRS = {
    'cod_cifs': COD,
    'icsd_cifs': ICSD,
    'mp_cifs': MP,
}

def count_rows(path: Path) -> str:
    try:
        if not path.exists():
            return "missing"
        df = pd.read_parquet(path)
        return str(len(df))
    except Exception as e:
        return f"error: {e}" 

print("=== Dara 3.0 Data Status ===")
print(f"Repo: {REPO}")
print("\n[Indexes]")
for name, p in FILES.items():
    print(f"- {name:24} : {count_rows(p)}")

print("\n[Directories]")
for name, d in DIRS.items():
    state = "present" if d.exists() else "missing"
    # Avoid recursive count (can be huge); just sample a few files
    sample = None
    if d.exists():
        try:
            sample = next(d.rglob('*.cif'))
            sample = sample.relative_to(REPO)
        except StopIteration:
            sample = "(no .cif found)"
        except Exception:
            sample = "(scan error)"
    print(f"- {name:24} : {state}  {f'example: {sample}' if sample else ''}")

print("\nTip: Use scripts/setup_databases.ps1 to build or refresh these datasets.")
