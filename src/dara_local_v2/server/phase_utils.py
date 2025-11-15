"""Utility functions for phase analysis results in dara_local_v2.

This module adapts logic from the streamlined_phase_analysis notebooks
for use in the web/worker pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd
from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


def phase_result_to_dict(phase_result: Any) -> Dict[str, Any] | None:
    """Convert PhaseResult-like object to JSON-serialisable dict.

    The implementation follows the helper in the streamlined notebook.
    """

    if phase_result is None:
        return None

    def convert_value(val: Any) -> Any:
        if isinstance(val, tuple):
            return list(val)
        if isinstance(val, (int, float, str, bool)) or val is None:
            return val
        return str(val)

    result_dict: Dict[str, Any] = {}
    for key in [
        "spacegroup_no",
        "hermann_mauguin",
        "xray_density",
        "rphase",
        "unit",
        "gewicht",
        "gewicht_name",
        "a",
        "b",
        "c",
        "alpha",
        "beta",
        "gamma",
    ]:
        if hasattr(phase_result, key):
            val = getattr(phase_result, key)
            result_dict[key] = convert_value(val)
    return result_dict


def extract_phase_info(solution: Any, custom_cif_dir: Path, database: str) -> pd.DataFrame:
    """Extract detailed crystallographic information from a search result.

    Returns a pandas DataFrame mirroring the notebook structure.
    """

    from pathlib import Path as _Path

    phase_data = []

    # solution.phases is a list of lists; each inner list is candidate phases
    phase_list = [phases[0] for phases in solution.phases]
    lst_data = getattr(solution.refinement_result, "lst_data", None)
    phase_results_source = getattr(lst_data, "phases_results", None)

    for idx, phase in enumerate(phase_list):
        try:
            structure = Structure.from_file(str(phase.path))
            phase_name = _Path(phase.path).stem

            # Resolve PhaseResult regardless of container type
            phase_result = None
            if isinstance(phase_results_source, dict):
                phase_result = phase_results_source.get(phase_name)
                if phase_result is None:
                    for key, value in phase_results_source.items():
                        key_name = None
                        if isinstance(key, (str, _Path)):
                            key_name = _Path(key).stem
                        else:
                            key_name = getattr(value, "phase_name", None)
                        if key_name == phase_name:
                            phase_result = value
                            break
            elif isinstance(phase_results_source, (list, tuple)):
                if idx < len(phase_results_source):
                    phase_result = phase_results_source[idx]
            elif phase_results_source is not None:
                candidate_name = getattr(phase_results_source, "phase_name", None)
                if candidate_name == phase_name:
                    phase_result = phase_results_source

            lattice = structure.lattice
            sga = SpacegroupAnalyzer(structure)
            crystal_system = sga.get_crystal_system()

            # Determine source: custom vs database
            if custom_cif_dir and str(custom_cif_dir) in str(phase.path):
                source = "Custom"
            else:
                source = database

            weight_pct = 0.0
            if phase_result is not None and hasattr(phase_result, "gewicht"):
                g = getattr(phase_result, "gewicht")
                if isinstance(g, (int, float)):
                    weight_pct = float(g)
                elif isinstance(g, tuple) and g:
                    weight_pct = float(g[0])

            phase_info = {
                "Source": source,
                "Phase Name": phase_name,
                "Formula": structure.composition.reduced_formula,
                "Space Group": structure.get_space_group_info()[0],
                "SG Number": structure.get_space_group_info()[1],
                "Crystal System": crystal_system,
                "a (Å)": f"{lattice.a:.4f}",
                "b (Å)": f"{lattice.b:.4f}",
                "c (Å)": f"{lattice.c:.4f}",
                "α (°)": f"{lattice.alpha:.2f}",
                "β (°)": f"{lattice.beta:.2f}",
                "γ (°)": f"{lattice.gamma:.2f}",
                "Weight %": f"{weight_pct:.2f}",
            }
            phase_data.append(phase_info)
        except Exception:  # noqa: BLE001
            # For robustness, skip phases we cannot parse
            continue

    return pd.DataFrame(phase_data)


def export_phase_search_report(
    solution: Any,
    solution_number: int,
    output_dir: Path,
    custom_cif_dir: Path,
    database: str,
) -> Path:
    """Export a comprehensive report for a single solution.

    The structure mirrors the notebook's export helper:
    - refinement_plot.html
    - identified_phases.csv
    - refinement_stats.json
    - cif_files/*
    - summary.txt
    """

    import json
    import shutil

    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir = output_dir / f"solution_{solution_number}"
    report_dir.mkdir(exist_ok=True)

    cif_dir = report_dir / "cif_files"
    cif_dir.mkdir(exist_ok=True)

    # 1. Plot as HTML
    try:
        fig = solution.visualize()
        plot_path = report_dir / "refinement_plot.html"
        fig.write_html(str(plot_path))
    except Exception:  # noqa: BLE001
        plot_path = None

    # 2. Phase table CSV
    phase_info = None
    try:
        phase_info = extract_phase_info(solution, custom_cif_dir=custom_cif_dir, database=database)
        csv_path = report_dir / "identified_phases.csv"
        phase_info.to_csv(csv_path, index=False)
    except Exception:  # noqa: BLE001
        phase_info = None

    # 3. Stats JSON
    try:
        lst_data = solution.refinement_result.lst_data
        phase_results_dict: Dict[str, Any] = {}
        for phase_name, phase_result in getattr(lst_data, "phases_results", {}).items():
            phase_results_dict[phase_name] = phase_result_to_dict(phase_result)

        stats = {
            "solution_number": solution_number,
            "pattern_name": lst_data.pattern_name,
            "rwp": lst_data.rwp,
            "rp": getattr(lst_data, "rp", None),
            "gof": getattr(lst_data, "gof", None),
            "num_phases": len(solution.phases),
            "phase_results": phase_results_dict,
        }

        json_path = report_dir / "refinement_stats.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        pass

    # 4. Copy CIF files
    try:
        phase_list = [phases[0] for phases in solution.phases]
        for i, phase in enumerate(phase_list, 1):
            src_path = Path(phase.path)
            dest_path = cif_dir / f"{i:02d}_{src_path.name}"
            shutil.copy2(src_path, dest_path)
    except Exception:  # noqa: BLE001
        pass

    # 5. Summary text
    try:
        summary_path = report_dir / "summary.txt"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write(f"PHASE SEARCH REPORT - Solution {solution_number}\n")
            f.write("=" * 70 + "\n\n")
            try:
                lst_data = solution.refinement_result.lst_data
                f.write(f"Pattern: {lst_data.pattern_name}\n")
                f.write(f"Rwp: {lst_data.rwp:.2f}%\n")
                f.write(f"Number of phases: {len(solution.phases)}\n\n")
            except Exception:  # noqa: BLE001
                pass

            if phase_info is not None and not phase_info.empty:
                f.write("-" * 70 + "\n")
                f.write("IDENTIFIED PHASES:\n")
                f.write("-" * 70 + "\n\n")
                f.write(phase_info.to_string(index=False))
                f.write("\n\n")

            f.write("-" * 70 + "\n")
            f.write("FILES:\n")
            f.write("-" * 70 + "\n")
            f.write("- refinement_plot.html\n")
            f.write("- identified_phases.csv\n")
            f.write("- refinement_stats.json\n")
            f.write("- cif_files/\n")
            f.write("- summary.txt\n")
    except Exception:  # noqa: BLE001
        pass

    return report_dir
