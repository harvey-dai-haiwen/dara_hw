import os
import re
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERN_EXTS = {'.xrdml', '.xrd'}
ELEM_RE = re.compile(r"[A-Z][a-z]?")


def extract_elements_from_stem(stem: str) -> list[str]:
    """Extract unique element symbols from a filename stem.
    Strategy:
      - Split by '-' into chemical parts/components
      - For each part, cut at first '_' to drop weights/time/temperature tokens
      - Run regex [A-Z][a-z]? to extract element symbols
      - Return sorted unique set
    """
    elems = set()
    for part in stem.split('-'):
        base = part.split('_', 1)[0]
        if not base or base.lower().endswith('min'):
            continue
        for e in ELEM_RE.findall(base):
            elems.add(e)
    return sorted(elems)


def find_xrd_files(root: Path) -> list[Path]:
    files = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in PATTERN_EXTS:
                files.append(Path(dirpath) / fn)
    return sorted(files)


def main() -> int:
    files = find_xrd_files(ROOT)
    out_csv = ROOT / 'dataset' / 'xrd_elements.csv'
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for path in files:
        rel = path.relative_to(ROOT)
        stem = path.stem
        elements = extract_elements_from_stem(stem)
        rows.append({
            'path': str(rel).replace('\\', '/'),
            'filename': path.name,
            'group': rel.parts[0] if len(rel.parts) > 0 else '',
            'elements': ';'.join(elements),
            'unique_elements_count': len(elements),
        })

    with out_csv.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['path', 'filename', 'group', 'elements', 'unique_elements_count'])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Found {len(rows)} XRD files. Wrote: {out_csv}")
    # Print a few examples
    for r in rows[:10]:
        print(f"- {r['path']}: {r['elements']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
