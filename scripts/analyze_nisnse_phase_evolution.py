from __future__ import annotations

import csv
import itertools
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from pymatgen.core import Structure


ROOT = Path(r"D:\XRD_Analysis\XRD_NiSnSe3\metadata\dara")
OUTPUT_ROOT = ROOT / "phase_evolution"
BATCHES = {
    "batch_001_nisnse_any": "Batch001: ICSD, Ni/Sn/Se any",
    "batch_002_nisnse_any_co": "Batch002: ICSD, Ni/Sn/Se any + C/O possible",
    "batch_003_nisnse_any_co_external_safe": "Batch003: ICSD + external DFT, Ni/Sn/Se any + C/O possible",
}
TEMPERATURE_ORDER = {
    "ball-milled": 0,
    "600C": 600,
    "700C": 700,
    "800C": 800,
    "900C": 900,
    "1000C": 1000,
}
TEMPERATURE_LABELS = {
    0: "BM",
    600: "600C",
    700: "700C",
    800: "800C",
    900: "900C",
    1000: "1000C",
}


@dataclass(frozen=True)
class PhaseFraction:
    phase: str
    key: str
    display: str
    weight_percent: float
    rphase: float | None
    formula: str | None


@dataclass(frozen=True)
class SolutionRecord:
    batch: str
    batch_label: str
    sample: str
    temperature: int
    rank: int
    rwp: float | None
    refinement_dir: Path
    plot_path: Path
    fraction_path: Path
    summary_path: Path
    phases: tuple[PhaseFraction, ...]


def sample_temperature(sample_name: str) -> int:
    if "ball-milled" in sample_name:
        return 0
    match = re.search(r"_(\d{3,4})C_", sample_name)
    if not match:
        raise ValueError(f"Cannot infer temperature from {sample_name}")
    return int(match.group(1))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def formula_from_cif(path: Path, cache: dict[Path, str | None]) -> str | None:
    path = path.resolve()
    if path in cache:
        return cache[path]
    try:
        formula = Structure.from_file(path).composition.reduced_formula
    except Exception:
        formula = None
    cache[path] = formula
    return formula


def phase_key(phase: str, formula: str | None) -> str:
    return formula or phase


def source_label(phase: str) -> str:
    lowered = phase.lower()
    if lowered.startswith("icsd_"):
        return f"ICSD {phase.split('_', 1)[1]}"
    if lowered.startswith("cod_"):
        return f"COD {phase.split('_', 1)[1]}"
    if lowered.startswith("mp_") or lowered.startswith("mp-"):
        return f"MP {phase.split('_', 1)[-1]}"
    return f"EXT {phase}"


def phase_display(phase: str, formula: str | None) -> str:
    label = source_label(phase)
    return f"{formula} ({label})" if formula else label


def load_solution_records(batch_name: str, batch_label: str, formula_cache: dict[Path, str | None]) -> list[SolutionRecord]:
    batch_dir = ROOT / batch_name
    records: list[SolutionRecord] = []
    for summary_path in sorted(batch_dir.glob("samples/*/summary.json")):
        sample_dir = summary_path.parent
        sample_name = sample_dir.name
        temperature = sample_temperature(sample_name)
        for refinement_dir in sorted((sample_dir / "searchmatch").glob("rank_*_representative")):
            match = re.search(r"rank_(\d+)", refinement_dir.name)
            if not match:
                continue
            rank = int(match.group(1))
            ref_summary_path = refinement_dir / "refinement_summary.json"
            fraction_path = refinement_dir / "phase_fractions.csv"
            plot_path = refinement_dir / "refinement_plot.html"
            if not ref_summary_path.exists() or not fraction_path.exists():
                continue
            ref_summary = read_json(ref_summary_path)
            phase_paths = [Path(p) for p in ref_summary.get("phase_paths", [])]
            formula_by_phase: dict[str, str | None] = {}
            for phase_path in phase_paths:
                formula_by_phase[phase_path.stem] = formula_from_cif(phase_path, formula_cache)

            phases: list[PhaseFraction] = []
            with fraction_path.open("r", encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle):
                    phase = row["phase"]
                    formula = formula_by_phase.get(phase)
                    try:
                        weight_percent = float(row["weight_percent"])
                    except (KeyError, ValueError):
                        weight_percent = 0.0
                    try:
                        rphase = float(row.get("rphase") or "nan")
                    except ValueError:
                        rphase = None
                    if rphase is not None and math.isnan(rphase):
                        rphase = None
                    key = phase_key(phase, formula)
                    phases.append(
                        PhaseFraction(
                            phase=phase,
                            key=key,
                            display=phase_display(phase, formula),
                            weight_percent=weight_percent,
                            rphase=rphase,
                            formula=formula,
                        )
                    )

            records.append(
                SolutionRecord(
                    batch=batch_name,
                    batch_label=batch_label,
                    sample=sample_name,
                    temperature=temperature,
                    rank=rank,
                    rwp=ref_summary.get("rwp"),
                    refinement_dir=refinement_dir,
                    plot_path=plot_path,
                    fraction_path=fraction_path,
                    summary_path=ref_summary_path,
                    phases=tuple(phases),
                )
            )
    return records


def route_score(route: tuple[SolutionRecord, ...]) -> float:
    score = 0.0
    for record in route:
        score += float(record.rwp or 100.0)
        score += 0.35 * (record.rank - 1)

    for left, right in itertools.pairwise(route):
        left_keys = {phase.key for phase in left.phases if phase.weight_percent >= 2.0}
        right_keys = {phase.key for phase in right.phases if phase.weight_percent >= 2.0}
        union = left_keys | right_keys
        overlap = left_keys & right_keys
        if union:
            score += 6.0 * (1.0 - len(overlap) / len(union))
        left_fraction = {phase.key: phase.weight_percent for phase in left.phases}
        right_fraction = {phase.key: phase.weight_percent for phase in right.phases}
        for key in overlap:
            score += 0.03 * abs(left_fraction.get(key, 0.0) - right_fraction.get(key, 0.0))

    all_keys = sorted({phase.key for record in route for phase in record.phases if phase.weight_percent >= 2.0})
    for key in all_keys:
        present = [any(phase.key == key and phase.weight_percent >= 2.0 for phase in record.phases) for record in route]
        for idx in range(1, len(present) - 1):
            if present[idx - 1] and not present[idx] and present[idx + 1]:
                score += 8.0
    return score


def unique_routes(records: list[SolutionRecord], limit: int = 3) -> list[tuple[float, tuple[SolutionRecord, ...]]]:
    by_temp: dict[int, list[SolutionRecord]] = {}
    for record in records:
        by_temp.setdefault(record.temperature, []).append(record)
    for candidates in by_temp.values():
        candidates.sort(key=lambda item: (float(item.rwp or 100.0), item.rank))
    temps = sorted(by_temp)
    all_routes = [tuple(route) for route in itertools.product(*(by_temp[temp] for temp in temps))]
    scored = sorted((route_score(route), route) for route in all_routes)

    selected: list[tuple[float, tuple[SolutionRecord, ...]]] = []
    seen_signatures: set[tuple[tuple[str, ...], ...]] = set()
    for score, route in scored:
        signature = tuple(tuple(sorted(phase.key for phase in record.phases if phase.weight_percent >= 2.0)) for record in route)
        if signature in seen_signatures:
            continue
        selected.append((score, route))
        seen_signatures.add(signature)
        if len(selected) >= limit:
            break
    return selected


def top_searchmatch_route(records: list[SolutionRecord]) -> tuple[SolutionRecord, ...]:
    by_temp: dict[int, list[SolutionRecord]] = {}
    for record in records:
        by_temp.setdefault(record.temperature, []).append(record)
    route: list[SolutionRecord] = []
    for temperature in sorted(by_temp):
        candidates = sorted(by_temp[temperature], key=lambda item: (item.rank, float(item.rwp or 100.0)))
        route.append(candidates[0])
    return tuple(route)


def write_route_csv(route: tuple[SolutionRecord, ...], path: Path) -> None:
    phase_keys = sorted({phase.key for record in route for phase in record.phases}, key=str)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["phase_key", "phase_display", *[TEMPERATURE_LABELS[r.temperature] for r in route]])
        display_by_key = {phase.key: phase.display for record in route for phase in record.phases}
        for key in phase_keys:
            row = [key, display_by_key.get(key, key)]
            for record in route:
                value = next((phase.weight_percent for phase in record.phases if phase.key == key), 0.0)
                row.append(round(value, 3))
            writer.writerow(row)


def plot_route(route: tuple[SolutionRecord, ...], title: str, path: Path) -> None:
    phase_keys = sorted(
        {phase.key for record in route for phase in record.phases if phase.weight_percent >= 1.0},
        key=lambda key: -max(
            (phase.weight_percent for record in route for phase in record.phases if phase.key == key),
            default=0.0,
        ),
    )
    display_by_key = {phase.key: phase.display for record in route for phase in record.phases}
    matrix = np.zeros((len(phase_keys), len(route)))
    for col, record in enumerate(route):
        for row, key in enumerate(phase_keys):
            matrix[row, col] = next((phase.weight_percent for phase in record.phases if phase.key == key), 0.0)

    height = max(4.5, min(12.0, 0.42 * len(phase_keys) + 1.9))
    fig, ax = plt.subplots(figsize=(11.5, height), constrained_layout=True)
    image = ax.imshow(matrix, aspect="auto", cmap="viridis", vmin=0, vmax=max(5.0, float(matrix.max())))
    ax.set_xticks(range(len(route)))
    ax.set_xticklabels([TEMPERATURE_LABELS[record.temperature] for record in route])
    ax.set_yticks(range(len(phase_keys)))
    ax.set_yticklabels([display_by_key.get(key, key) for key in phase_keys], fontsize=8)
    ax.set_title(title)
    ax.set_xlabel("Temperature series")
    ax.set_ylabel("Refined phase")
    for row in range(matrix.shape[0]):
        for col in range(matrix.shape[1]):
            if matrix[row, col] >= 1.0:
                ax.text(col, row, f"{matrix[row, col]:.0f}", ha="center", va="center", fontsize=7, color="white")
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("Weight percent")
    fig.savefig(path, dpi=220)
    plt.close(fig)


def format_formula_label(display: str) -> str:
    if " (" in display:
        formula, source = display.split(" (", 1)
        source = source.rstrip(")")
        formula = re.sub(r"([A-Z][a-z]?)(?=[A-Z]|\d|$)", r"\1 ", formula).strip()
        return f"{formula} ({source})"
    return display


def plot_route_sequence(route: tuple[SolutionRecord, ...], title: str, path: Path) -> None:
    phase_keys = sorted(
        {phase.key for record in route for phase in record.phases if phase.weight_percent >= 1.0},
        key=lambda key: -max(
            (phase.weight_percent for record in route for phase in record.phases if phase.key == key),
            default=0.0,
        ),
    )
    display_by_key = {phase.key: phase.display for record in route for phase in record.phases}
    x = np.arange(len(route))
    markers = ["o", "v", "^", "s", "D", "*", "P", "X", "<", ">", "h", "p"]

    fig, ax = plt.subplots(figsize=(12.8, 7.2), constrained_layout=True)
    for index, key in enumerate(phase_keys):
        y = [
            next((phase.weight_percent for phase in record.phases if phase.key == key), 0.0)
            for record in route
        ]
        ax.plot(
            x,
            y,
            marker=markers[index % len(markers)],
            linewidth=2.4,
            markersize=8,
            alpha=0.88,
            label=format_formula_label(display_by_key.get(key, key)),
        )

    ax.set_ylim(0, 100)
    ax.set_xlim(-0.25, len(route) - 0.75)
    ax.set_xticks(x)
    ax.set_xticklabels([TEMPERATURE_LABELS[record.temperature] for record in route], fontsize=12)
    ax.set_xlabel("Temperature (C)", fontsize=16)
    ax.set_ylabel("Composition (wt%)", fontsize=16)
    ax.text(
        0.02,
        0.95,
        title,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=22,
        fontweight="bold",
    )
    ax.grid(axis="y", color="#d9dde2", linewidth=0.7, alpha=0.55)
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(0.02, 0.70),
        frameon=True,
        framealpha=0.88,
        facecolor="white",
        edgecolor="#cfd4da",
        fontsize=10,
    )
    for spine in ax.spines.values():
        spine.set_linewidth(1.4)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def route_notes(route: tuple[SolutionRecord, ...]) -> list[str]:
    notes: list[str] = []
    all_keys = sorted({phase.key for record in route for phase in record.phases if phase.weight_percent >= 2.0})
    for key in all_keys:
        values = [
            next((phase.weight_percent for phase in record.phases if phase.key == key), 0.0)
            for record in route
        ]
        present = [value >= 2.0 for value in values]
        if any(present[idx - 1] and not present[idx] and present[idx + 1] for idx in range(1, len(present) - 1)):
            notes.append(f"{key}: has a present-absent-present gap above 2 wt%; treat as suspicious unless chemistry supports it.")
    return notes


def write_completeness_audit(all_records: list[SolutionRecord], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "batch",
                "sample",
                "temperature",
                "rank",
                "rwp",
                "has_refinement_plot",
                "has_phase_fractions_csv",
                "has_phase_fractions_json",
                "phase_count",
                "refinement_dir",
            ]
        )
        for record in sorted(all_records, key=lambda r: (r.batch, r.temperature, r.rank)):
            writer.writerow(
                [
                    record.batch,
                    record.sample,
                    record.temperature,
                    record.rank,
                    record.rwp,
                    record.plot_path.exists() and record.plot_path.stat().st_size > 0,
                    record.fraction_path.exists() and record.fraction_path.stat().st_size > 0,
                    (record.refinement_dir / "phase_fractions.json").exists(),
                    len(record.phases),
                    record.refinement_dir,
                ]
            )


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    formula_cache: dict[Path, str | None] = {}
    all_records: list[SolutionRecord] = []
    report_lines = [
        "# NiSnSe3 Dara phase evolution",
        "",
        "Fractions are refined weight percentages exported from Dara/BGMN refinement outputs.",
        "For these pre-existing batches, each saved solution was re-refined with the first CIF from each summarized phase group, so the maps are representative refinements rather than the original in-memory SearchResult objects.",
        "",
    ]

    for batch_name, batch_label in BATCHES.items():
        records = load_solution_records(batch_name, batch_label, formula_cache)
        all_records.extend(records)
        routes = unique_routes(records, limit=3)
        report_lines.extend([f"## {batch_label}", ""])
        report_lines.append(f"Loaded {len(records)} saved solution refinements.")
        report_lines.append("")

        batch_output = OUTPUT_ROOT / batch_name
        batch_output.mkdir(parents=True, exist_ok=True)
        top_route = top_searchmatch_route(records)
        top_sequence_png = batch_output / "top_searchmatch_selected_sequence.png"
        top_csv = batch_output / "top_searchmatch_phase_map.csv"
        plot_route_sequence(top_route, "Top search-match sequence", top_sequence_png)
        write_route_csv(top_route, top_csv)
        top_ranks = ", ".join(f"{TEMPERATURE_LABELS[r.temperature]}:rank{r.rank}/Rwp{r.rwp}" for r in top_route)
        report_lines.extend(
            [
                "### Top search-match",
                "",
                f"Ranks: {top_ranks}",
                "",
                f"Selected sequence: `{top_sequence_png}`",
                "",
                f"Table: `{top_csv}`",
                "",
            ]
        )

        for route_index, (score, route) in enumerate(routes, start=1):
            png_path = batch_output / f"route_{route_index:02d}_phase_map.png"
            sequence_png_path = batch_output / f"route_{route_index:02d}_selected_sequence.png"
            csv_path = batch_output / f"route_{route_index:02d}_phase_map.csv"
            plot_route(route, f"{batch_label} / route {route_index}", png_path)
            plot_route_sequence(route, "Selected sequence", sequence_png_path)
            write_route_csv(route, csv_path)
            ranks = ", ".join(f"{TEMPERATURE_LABELS[r.temperature]}:rank{r.rank}/Rwp{r.rwp}" for r in route)
            report_lines.extend(
                [
                    f"### Route {route_index}",
                    "",
                    f"Score: {score:.2f}",
                    "",
                    f"Ranks: {ranks}",
                    "",
                    f"Map: `{png_path}`",
                    "",
                    f"Selected sequence: `{sequence_png_path}`",
                    "",
                    f"Table: `{csv_path}`",
                    "",
                ]
            )
            notes = route_notes(route)
            if notes:
                report_lines.append("Continuity flags:")
                report_lines.extend(f"- {note}" for note in notes)
                report_lines.append("")

    audit_path = OUTPUT_ROOT / "phase_fraction_refinement_completeness.csv"
    write_completeness_audit(all_records, audit_path)
    report_lines.extend(
        [
            "## Completeness",
            "",
            f"Audit CSV: `{audit_path}`",
            "",
            f"Saved solution refinements loaded: {len(all_records)}",
            "",
        ]
    )
    (OUTPUT_ROOT / "phase_evolution_report.md").write_text("\n".join(report_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
