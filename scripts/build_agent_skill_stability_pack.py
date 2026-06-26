"""Build fixed real-XRD case packs for agent skill-stability benchmarking."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = Path(r"D:\XRD_Analysis\metadata\dara_agent_skill_stability_20260605")


def _copy_first_cifs(source: Path, dest: Path, limit: int = 20) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    copied = 0
    for cif in sorted(source.glob("*.cif"))[:limit]:
        shutil.copy2(cif, dest / cif.name)
        copied += 1
    return copied


def _copy_json_candidates(json_path: Path, dest: Path, limit: int = 20) -> int:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    dest.mkdir(parents=True, exist_ok=True)
    copied = 0
    for raw in data["candidate_paths"][:limit]:
        cif = Path(raw)
        if cif.exists():
            shutil.copy2(cif, dest / cif.name)
            copied += 1
    return copied


def main() -> int:
    PACK_ROOT.mkdir(parents=True, exist_ok=True)
    cases = [
        {
            "case_id": "ymo_real",
            "label": "DTMA YMoO3 one-pot 1200C",
            "xrd": r"D:\XRD_Analysis\DTMA_YMoO3\20231212_YCl3Onepot_1200.xy",
            "source": r"D:\XRD_Analysis\DTMA_YMoO3\metadata\dara\dtma_ymo3_icsd_40cpu_dryrun\candidates\raw",
            "source_type": "dir",
        },
        {
            "case_id": "nisnse_real",
            "label": "NiSnSe3 700C 60s",
            "xrd": r"D:\XRD_Analysis\XRD_NiSnSe3\20260428_NiSnSe3_700C_60s_001.xy",
            "source": r"D:\XRD_Analysis\XRD_NiSnSe3\metadata\dara\batch_001_nisnse_any\samples\20260428_NiSnSe3_700C_60s_001\candidates\raw",
            "source_type": "dir",
        },
        {
            "case_id": "znvo_real",
            "label": "VO2 plus ZnO 1050C 4h",
            "xrd": r"D:\XRD_Analysis\VO2+ZnO_Sigma_IMRE_1050_4h.xy",
            "source": str(ROOT / "benchmarks" / "engine_compare" / "gsas_runs"),
            "source_type": "nested_candidate_phase_dirs",
        },
    ]

    manifest_cases = []
    for case in cases:
        candidate_dir = PACK_ROOT / "candidate_packs" / case["case_id"]
        if candidate_dir.exists():
            shutil.rmtree(candidate_dir)
        source = Path(case["source"])
        if case["source_type"] == "json_candidates":
            copied = _copy_json_candidates(source, candidate_dir)
        elif case["source_type"] == "nested_candidate_phase_dirs":
            candidate_dir.mkdir(parents=True, exist_ok=True)
            copied = 0
            for candidate in sorted(source.glob("znvo_*/candidate_phase.cif"))[:20]:
                shutil.copy2(candidate, candidate_dir / f"{candidate.parent.name}.cif")
                copied += 1
        else:
            copied = _copy_first_cifs(source, candidate_dir)
        if copied == 0:
            raise RuntimeError(f"No CIFs copied for {case['case_id']} from {source}")
        case_manifest = {
            "case_id": case["case_id"],
            "label": case["label"],
            "xrd": case["xrd"],
            "candidate_dir": str(candidate_dir),
            "candidate_count": copied,
            "wavelength": "Cu",
        }
        case_json = PACK_ROOT / f"{case['case_id']}.json"
        case_json.write_text(json.dumps(case_manifest, indent=2), encoding="utf-8")
        case_manifest["case_json"] = str(case_json)
        manifest_cases.append(case_manifest)

    manifest = {
        "pack_root": str(PACK_ROOT),
        "cpu_target_fraction": 0.60,
        "logical_threads": 32,
        "target_logical_cpu_percent": 60,
        "cases": manifest_cases,
    }
    (PACK_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
