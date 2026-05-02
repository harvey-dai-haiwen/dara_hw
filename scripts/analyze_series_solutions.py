from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from datetime import datetime
from itertools import product
from pathlib import Path


POST_SELECTION_PHASE_PARAMS = {
    "gewicht": "0_0",
    "lattice_range": 0.01,
    "k1": "0_0^0.03",
    "k2": "fixed",
    "b1": "0_0^0.02",
    "rp": 3,
}

POST_SELECTION_REFINEMENT_OVERRIDES = {
    "eps1": 0,
    "eps2": "0_-0.08^0.08",
}


def slugify(text: str) -> str:
    lowered = text.lower().strip()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "sample"


def find_or_create_batch(metadata_root: Path, batch_id: str | None = None) -> tuple[str, Path]:
    """Find or create a batch directory.
    
    Args:
        metadata_root: metadata/dara root directory
        batch_id: explicit batch ID (e.g., "batch_001"). If None, auto-detect or create new.
        
    Returns:
        tuple of (batch_id, batch_path)
    """
    if batch_id:
        batch_dir = metadata_root / batch_id
    else:
        batch_dirs = sorted([d for d in metadata_root.iterdir() if d.is_dir() and d.name.startswith("batch_")])
        if batch_dirs:
            batch_dir = batch_dirs[-1]
            batch_id = batch_dir.name
        else:
            batch_id = "batch_001"
            batch_dir = metadata_root / batch_id
    
    batch_dir.mkdir(parents=True, exist_ok=True)
    return batch_id, batch_dir


def parse_temperature(sample_name: str) -> tuple[int, int, str]:
    lowered = sample_name.lower()
    if "ball-milled" in lowered:
        return (0, 25, "BM")

    match = re.search(r"_(?P<temp>\d+)c_", lowered)
    if match is None:
        return (10_000, 10_000, sample_name)

    temperature_c = int(match.group("temp"))
    return (temperature_c, temperature_c, f"{temperature_c}")


def phase_tokens(formula: str) -> set[str]:
    return set(re.findall(r"([A-Z][a-z]?)", formula))


def is_elemental_formula(formula: str) -> bool:
    return len(phase_tokens(formula)) == 1


def has_selenium(formula: str) -> bool:
    return "Se" in phase_tokens(formula)


def is_non_selenide_intermetallic(formula: str) -> bool:
    tokens = phase_tokens(formula)
    return "Se" not in tokens and len(tokens) > 1


def weighted_jaccard(weights_a: dict[str, float], weights_b: dict[str, float]) -> float:
    keys = set(weights_a) | set(weights_b)
    if not keys:
        return 0.0

    numerator = sum(min(weights_a.get(key, 0.0), weights_b.get(key, 0.0)) for key in keys)
    denominator = sum(max(weights_a.get(key, 0.0), weights_b.get(key, 0.0)) for key in keys)
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def discover_latest_run_dir(metadata_root: Path, sample_path: Path, database_name: str) -> Path:
    """Find the latest completed run directory for a sample.
    
    Supports both batch structure (batch_*/samples/{sample_slug}) and legacy structure ({timestamp}-{sample_slug}).
    """
    sample_slug = slugify(sample_path.stem)
    
    batch_dirs = sorted([d for d in metadata_root.iterdir() if d.is_dir() and d.name.startswith("batch_")], reverse=True)
    for batch_dir in batch_dirs:
        sample_dir = batch_dir / "samples" / sample_slug
        if (sample_dir / database_name.lower() / "summary.json").exists():
            return sample_dir
    
    matches = sorted(metadata_root.glob(f"*-{sample_slug}"), reverse=True)
    if not matches:
        raise FileNotFoundError(f"No Dara metadata run found for {sample_path.name}")

    for run_dir in matches:
        if (run_dir / database_name.lower() / "summary.json").exists():
            return run_dir

    raise FileNotFoundError(
        f"No completed Dara metadata run found for {sample_path.name} and database {database_name}"
    )


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def parse_formula_components(formula: str) -> tuple[dict[str, str], list[str]]:
    components: dict[str, str] = {}
    order: list[str] = []
    for element, count in re.findall(r"([A-Z][a-z]?)([0-9]+(?:\.[0-9]+)?)?", formula):
        if element not in components:
            order.append(element)
        components[element] = count or "1"
    return components, order


def format_formula(components: dict[str, str], order: list[str]) -> str:
    return " ".join(f"{element}{components[element]}" for element in order if element in components)


def normalize_formula(formula: str, preferred_formula: str | None = None) -> str:
    components, order = parse_formula_components(formula)
    if not components:
        return formula

    if preferred_formula:
        _, preferred_order = parse_formula_components(preferred_formula)
        if preferred_order and set(preferred_order) == set(order):
            order = preferred_order
    return format_formula(components, order)


def extract_cif_formula(cif_path: Path, preferred_formula: str | None = None) -> str | None:
    if not cif_path.exists():
        return None

    raw_formula: str | None = None
    for line in cif_path.read_text(encoding="utf-8", errors="ignore").splitlines()[:120]:
        stripped = line.strip()
        if stripped.startswith("_chemical_formula_structural"):
            raw_formula = stripped.split(None, 1)[1].strip("'\"")
            break
        if stripped.startswith("_chemical_formula_sum"):
            raw_formula = stripped.split(None, 1)[1].strip("'\"")
            break

    if raw_formula is None:
        return None
    return normalize_formula(raw_formula, preferred_formula)


def build_formula_lookup(candidate_refinement: dict, jobflow_root: Path) -> dict[str, str]:
    formula_lookup: dict[str, str] = {}
    job_dirs = sorted(jobflow_root.glob("job_*"))
    cif_dir = job_dirs[-1] / "dara_cifs" if job_dirs else None
    for phase_bucket in candidate_refinement.get("phase_buckets", []):
        for cluster in phase_bucket.get("clusters", []):
            head_formula = cluster.get("head_formula", "unknown")
            for cif_stem in cluster.get("cif_stems", []):
                cif_formula = None
                if cif_dir is not None:
                    cif_formula = extract_cif_formula(cif_dir / f"{cif_stem}.cif", head_formula)
                formula_lookup[cif_stem] = cif_formula or head_formula
    return formula_lookup


def aggregate_formula_weights(candidate_refinement: dict, summary: dict) -> tuple[dict[str, float], list[dict[str, object]]]:
    formula_lookup = build_formula_lookup(candidate_refinement, Path(summary["jobflow_root"]))
    formula_weights: dict[str, float] = defaultdict(float)
    formula_phases: dict[str, list[str]] = defaultdict(list)
    for phase_summary in candidate_refinement.get("refinement", []):
        phase_name = phase_summary["phase"]
        formula_name = formula_lookup.get(phase_name, phase_name)
        formula_weights[formula_name] += float(phase_summary["weight_fraction"])
        formula_phases[formula_name].append(phase_name)

    formulas = []
    for formula_name, weight_fraction in sorted(formula_weights.items(), key=lambda item: item[1], reverse=True):
        formulas.append(
            {
                "formula": formula_name,
                "weight_fraction": weight_fraction,
                "phases": sorted(formula_phases[formula_name]),
            }
        )
    return dict(formula_weights), formulas


def format_formula_weight_summary(formula_weights: dict[str, float]) -> list[dict[str, object]]:
    return [
        {"formula": formula_name, "weight_fraction": weight_fraction}
        for formula_name, weight_fraction in sorted(formula_weights.items(), key=lambda item: item[1], reverse=True)
    ]


def get_latest_cif_dir(summary: dict) -> Path | None:
    jobflow_root = Path(summary["jobflow_root"])
    job_dirs = sorted(jobflow_root.glob("job_*"))
    if not job_dirs:
        return None
    cif_dir = job_dirs[-1] / "dara_cifs"
    return cif_dir if cif_dir.exists() else None


def get_candidate_phase_names(candidate: dict) -> list[str]:
    phase_names = [entry["phase"] for entry in candidate.get("refinement", [])]
    if phase_names:
        return phase_names

    names_from_buckets: list[str] = []
    for phase_bucket in candidate.get("phase_buckets", []):
        for cluster in phase_bucket.get("clusters", []):
            names_from_buckets.extend(cluster.get("cif_stems", []))
    return list(dict.fromkeys(names_from_buckets))


def build_phase_to_formula_lookup(candidate: dict) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for formula_entry in candidate.get("formulas", []):
        formula_name = formula_entry["formula"]
        for phase_name in formula_entry.get("phases", []):
            lookup[phase_name] = formula_name
    return lookup


def run_post_selection_refinement(
    samples: list[dict],
    chosen_sequence: dict,
    analysis_dir: Path,
) -> tuple[list[dict[str, object]], dict]:
    from dara.refine import do_refinement

    post_refine_root = analysis_dir / "post-refinement"
    post_refine_root.mkdir(parents=True, exist_ok=True)

    updated_candidates = []
    post_results: list[dict[str, object]] = []

    for sample, candidate in zip(samples, chosen_sequence["candidates"]):
        sample_slug = slugify(Path(sample["sample_name"]).stem)
        sample_refine_dir = post_refine_root / sample_slug
        sample_refine_dir.mkdir(parents=True, exist_ok=True)

        cif_dir = get_latest_cif_dir(sample["summary"])
        phase_names = get_candidate_phase_names(candidate)
        phase_paths = []
        if cif_dir is not None:
            for phase_name in phase_names:
                cif_path = cif_dir / f"{phase_name}.cif"
                if cif_path.exists():
                    phase_paths.append(cif_path)

        phase_to_formula = build_phase_to_formula_lookup(candidate)
        fallback_candidate = {
            **candidate,
            "post_refined": False,
        }

        if not phase_paths:
            post_results.append(
                {
                    "sample_name": sample["sample_name"],
                    "status": "skipped",
                    "reason": "phase CIF files not found in latest jobflow output",
                    "artifact_dir": sample_refine_dir.as_posix(),
                }
            )
            updated_candidates.append(fallback_candidate)
            continue

        try:
            bgmn_threads = int(sample["run_note"].get("bgmn_threads", 4))
            refinement_params = {
                "n_threads": max(1, bgmn_threads),
                **POST_SELECTION_REFINEMENT_OVERRIDES,
            }
            result = do_refinement(
                pattern_path=sample["sample_path"],
                phases=phase_paths,
                wavelength=sample["run_note"].get("wavelength", "Cu"),
                instrument_profile=sample["run_note"].get("instrument_profile", "Aeris-fds-Pixcel1d-Medipix3"),
                working_dir=sample_refine_dir,
                phase_params=POST_SELECTION_PHASE_PARAMS,
                refinement_params=refinement_params,
                show_progress=False,
            )

            phase_weights = result.get_phase_weights(normalize=True)
            refined_formula_weights: dict[str, float] = defaultdict(float)
            for phase_name, weight_fraction in phase_weights.items():
                formula_name = phase_to_formula.get(phase_name, phase_name)
                refined_formula_weights[formula_name] += float(weight_fraction)

            refined_formulas = format_formula_weight_summary(dict(refined_formula_weights))
            refined_candidate = {
                **candidate,
                "rwp": float(getattr(result.lst_data, "rwp", candidate.get("rwp") or sample["best_rwp"])),
                "formula_weights": dict(refined_formula_weights),
                "formulas": [
                    {
                        "formula": item["formula"],
                        "weight_fraction": item["weight_fraction"],
                        "phases": sorted(
                            [name for name, formula_name in phase_to_formula.items() if formula_name == item["formula"]]
                        ),
                    }
                    for item in refined_formulas
                ],
                "post_refined": True,
            }

            html_path = sample_refine_dir / "post_refinement_plot.html"
            figure = result.visualize(diff_offset=True)
            figure.write_html(html_path.as_posix())

            details = {
                "sample_name": sample["sample_name"],
                "status": "ok",
                "rwp": refined_candidate["rwp"],
                "formula_weights": refined_candidate["formula_weights"],
                "artifact_dir": sample_refine_dir.as_posix(),
                "plot": html_path.as_posix(),
            }
            (sample_refine_dir / "post_refinement_summary.json").write_text(
                json.dumps(details, indent=2), encoding="utf-8"
            )
            post_results.append(details)
            updated_candidates.append(refined_candidate)
        except Exception as exc:
            post_results.append(
                {
                    "sample_name": sample["sample_name"],
                    "status": "error",
                    "error": str(exc),
                    "artifact_dir": sample_refine_dir.as_posix(),
                }
            )
            updated_candidates.append(fallback_candidate)

    refined_sequence = {**chosen_sequence, "candidates": updated_candidates}
    return post_results, refined_sequence


def extract_candidate_rwps(summary: dict) -> list[dict]:
    candidate_refinements = summary.get("candidate_refinements")
    if candidate_refinements:
        return candidate_refinements

    return [
        {
            "rank": 1,
            "rwp": summary.get("best_rwp"),
            "phase_buckets": summary.get("top_candidate_groups", [{}])[0].get("phase_buckets", []),
            "refinement": summary.get("best_refinement", []),
        }
    ]


def load_series_data(series_dir: Path, database_name: str) -> list[dict[str, object]]:
    metadata_root = series_dir / "metadata" / "dara"
    sample_paths = sorted(series_dir.glob("*.xy"), key=lambda path: parse_temperature(path.name))
    samples: list[dict[str, object]] = []
    for sample_path in sample_paths:
        run_dir = discover_latest_run_dir(metadata_root, sample_path, database_name)
        run_note = load_json(run_dir / "run_note.json")
        summary = load_json(run_dir / database_name.lower() / "summary.json")
        order_key, temperature_c, x_label = parse_temperature(sample_path.name)
        candidates = []
        for candidate_refinement in extract_candidate_rwps(summary):
            formula_weights, formulas = aggregate_formula_weights(candidate_refinement, summary)
            candidates.append(
                {
                    "rank": int(candidate_refinement["rank"]),
                    "rwp": candidate_refinement.get("rwp", summary.get("best_rwp")),
                    "phase_buckets": candidate_refinement.get("phase_buckets", []),
                    "refinement": candidate_refinement.get("refinement", []),
                    "formula_weights": formula_weights,
                    "formulas": formulas,
                }
            )

        samples.append(
            {
                "sample_name": sample_path.name,
                "sample_path": sample_path,
                "run_dir": run_dir,
                "summary": summary,
                "run_note": run_note,
                "order_key": order_key,
                "temperature_c": temperature_c,
                "x_label": x_label,
                "best_rwp": float(summary.get("best_rwp", math.inf)),
                "candidates": candidates,
            }
        )
    return samples


def candidate_penalty(sample: dict, candidate: dict) -> tuple[float, list[str]]:
    penalty = 0.0
    reasons: list[str] = []
    temperature_c = sample["temperature_c"]

    if candidate.get("rwp") is not None:
        penalty += max(0.0, float(candidate["rwp"]) - sample["best_rwp"]) * 0.5
    penalty += 0.35 * max(0, int(candidate["rank"]) - 1)

    if temperature_c >= 500:
        for formula_name, weight_fraction in candidate["formula_weights"].items():
            if is_elemental_formula(formula_name):
                penalty += 4.0 * weight_fraction
                reasons.append(f"elemental phase {formula_name} persists after heating")
            elif is_non_selenide_intermetallic(formula_name):
                penalty += 3.5 * weight_fraction
                reasons.append(f"non-selenide intermetallic {formula_name} appears after heating")
            elif not has_selenium(formula_name):
                penalty += 2.0 * weight_fraction
                reasons.append(f"phase {formula_name} lacks selenium in a reacted sample")

    return penalty, reasons


def transition_score(previous_sample: dict, previous_candidate: dict, current_sample: dict, current_candidate: dict) -> tuple[float, list[str]]:
    continuity = weighted_jaccard(previous_candidate["formula_weights"], current_candidate["formula_weights"])
    factor = 0.4 if previous_sample["x_label"] == "BM" else 1.0
    score = 4.5 * factor * continuity
    reasons: list[str] = []

    if continuity < 0.15 and current_sample["temperature_c"] >= 500:
        reasons.append(
            f"low continuity from {previous_sample['x_label']} to {current_sample['x_label']} (weighted overlap {continuity:.2f})"
        )
        score -= 0.8

    previous_major = {name for name, weight in previous_candidate["formula_weights"].items() if weight >= 0.15}
    current_major = {name for name, weight in current_candidate["formula_weights"].items() if weight >= 0.15}
    turnover = len(previous_major.symmetric_difference(current_major))
    if turnover >= 4 and current_sample["temperature_c"] >= 500:
        reasons.append(
            f"too many major-phase swaps between {previous_sample['x_label']} and {current_sample['x_label']}"
        )
        score -= 0.5 * (turnover - 3)

    return score, reasons


def evaluate_sequence(samples: list[dict], candidate_indices: tuple[int, ...]) -> dict[str, object]:
    chosen_candidates = [sample["candidates"][candidate_index] for sample, candidate_index in zip(samples, candidate_indices)]
    total_score = 0.0
    chemistry_penalty = 0.0
    continuity_score = 0.0
    per_sample_reasons: dict[str, list[str]] = defaultdict(list)
    transition_reasons: list[str] = []

    for sample, candidate in zip(samples, chosen_candidates):
        penalty, reasons = candidate_penalty(sample, candidate)
        chemistry_penalty += penalty
        total_score -= penalty
        if reasons:
            per_sample_reasons[sample["sample_name"]].extend(sorted(set(reasons)))

    for index in range(1, len(samples)):
        reward, reasons = transition_score(samples[index - 1], chosen_candidates[index - 1], samples[index], chosen_candidates[index])
        continuity_score += reward
        total_score += reward
        transition_reasons.extend(reasons)

    return {
        "score": total_score,
        "chemistry_penalty": chemistry_penalty,
        "continuity_score": continuity_score,
        "candidates": chosen_candidates,
        "indices": candidate_indices,
        "per_sample_reasons": dict(per_sample_reasons),
        "transition_reasons": sorted(set(transition_reasons)),
    }


def enumerate_sequences(samples: list[dict]) -> list[dict[str, object]]:
    sequence_scores = []
    candidate_ranges = [range(len(sample["candidates"])) for sample in samples]
    for candidate_indices in product(*candidate_ranges):
        sequence_scores.append(evaluate_sequence(samples, tuple(candidate_indices)))
    sequence_scores.sort(key=lambda item: item["score"], reverse=True)
    return sequence_scores


def choose_rejected_sequence(sequences: list[dict[str, object]]) -> dict[str, object]:
    chosen = sequences[0]
    for candidate_sequence in sequences[1:]:
        if candidate_sequence["chemistry_penalty"] > chosen["chemistry_penalty"] + 0.5:
            return candidate_sequence
        if candidate_sequence["continuity_score"] < chosen["continuity_score"] - 0.75:
            return candidate_sequence
    return sequences[1] if len(sequences) > 1 else sequences[0]


def collect_plot_formulas(sequence: dict) -> list[str]:
    max_weights: dict[str, float] = defaultdict(float)
    for candidate in sequence["candidates"]:
        for formula_name, weight_fraction in candidate["formula_weights"].items():
            max_weights[formula_name] = max(max_weights[formula_name], weight_fraction)
    selected = [name for name, weight in max_weights.items() if weight >= 0.03]
    return sorted(selected, key=lambda name: max_weights[name], reverse=True)


def render_sequence_plot(samples: list[dict], sequence: dict, title: str, subtitle: str, output_path: Path) -> None:
    import matplotlib.pyplot as plt

    formulas = collect_plot_formulas(sequence)
    x_values = [sample["temperature_c"] for sample in samples]
    x_tick_labels = [sample["x_label"] for sample in samples]
    markers = ["o", "v", "^", "s", "D", "*", "P", "X", "<", ">"]
    color_cycle = [
        "#2a9d8f",
        "#bc6c25",
        "#6c6fb1",
        "#c4458f",
        "#8fb339",
        "#d4a72c",
        "#8c6d31",
        "#6b7280",
        "#457b9d",
        "#e76f51",
    ]

    fig, ax = plt.subplots(figsize=(11.5, 7.2), dpi=180)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    for index, formula_name in enumerate(formulas):
        y_values = [100.0 * sequence["candidates"][sample_index]["formula_weights"].get(formula_name, 0.0) for sample_index in range(len(samples))]
        ax.plot(
            x_values,
            y_values,
            marker=markers[index % len(markers)],
            markersize=11,
            linewidth=2.5,
            color=color_cycle[index % len(color_cycle)],
            label=formula_name,
            alpha=0.9,
        )

    ax.set_ylim(0, 100)
    ax.set_xlim(min(x_values) - 50, max(x_values) + 60)
    ax.set_xticks(x_values)
    ax.set_xticklabels(x_tick_labels, fontsize=12)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.tick_params(axis="y", labelsize=12)
    ax.set_ylabel("Composition (wt%)", fontsize=16)
    ax.set_xlabel("Temperature (C)", fontsize=16)
    ax.grid(axis="y", alpha=0.15)
    for spine in ax.spines.values():
        spine.set_linewidth(1.6)

    legend = ax.legend(loc="center left", bbox_to_anchor=(0.01, 0.5), frameon=True, fontsize=12)
    legend.get_frame().set_alpha(0.92)
    legend.get_frame().set_edgecolor("#d1d5db")

    ax.text(0.02, 0.95, title, transform=ax.transAxes, fontsize=22, fontweight="bold", va="top")
    ax.text(0.98, 0.07, subtitle, transform=ax.transAxes, fontsize=12, ha="right", va="bottom")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def format_candidate_line(candidate: dict) -> str:
    parts = []
    for formula_entry in candidate["formulas"]:
        phase_list = ", ".join(formula_entry["phases"])
        parts.append(f"{formula_entry['formula']} {100.0 * formula_entry['weight_fraction']:.1f}% [{phase_list}]")
    rwp = "n/a" if candidate["rwp"] is None else f"{candidate['rwp']:.2f}"
    return f"rank {candidate['rank']} | Rwp {rwp} | " + "; ".join(parts)


def write_report(
    series_dir: Path,
    report_path: Path,
    analysis_dir: Path,
    samples: list[dict],
    chosen_sequence: dict,
    refined_chosen_sequence: dict,
    rejected_sequence: dict,
    chosen_plot_path: Path,
    chosen_refined_plot_path: Path,
    rejected_plot_path: Path,
    post_refinement_results: list[dict[str, object]],
    top_sequences: list[dict],
) -> None:
    lines: list[str] = []
    lines.append("# Dara Combined Series Report")
    lines.append("")
    lines.append(f"Series directory: {series_dir.as_posix()}")
    lines.append(f"Analysis artifacts: {analysis_dir.as_posix()}")
    lines.append("")
    lines.append("## Per-sample candidate solutions")
    lines.append("")
    for sample in samples:
        lines.append(f"### {sample['sample_name']}")
        lines.append(f"- best Rwp: {sample['best_rwp']:.2f}")
        lines.append(f"- number of candidate solutions: {len(sample['candidates'])}")
        for candidate in sample["candidates"]:
            lines.append(f"- {format_candidate_line(candidate)}")
        lines.append("")

    lines.append("## Selected continuity-consistent sequence")
    lines.append("")
    lines.append(f"- sequence score: {chosen_sequence['score']:.2f}")
    lines.append(f"- chemistry penalty: {chosen_sequence['chemistry_penalty']:.2f}")
    lines.append(f"- continuity score: {chosen_sequence['continuity_score']:.2f}")
    lines.append(f"- plot: {chosen_plot_path.as_posix()}")
    lines.append("")
    for sample, candidate in zip(samples, chosen_sequence["candidates"]):
        lines.append(f"- {sample['x_label']}: {format_candidate_line(candidate)}")
    lines.append("")
    lines.append("Reasoning:")
    for reason in chosen_sequence["transition_reasons"]:
        lines.append(f"- {reason}")
    if not chosen_sequence["transition_reasons"]:
        lines.append("- adjacent samples retain overlapping selenide families, so no abrupt discontinuity penalty was triggered")
    lines.append("")

    lines.append("## Post-selection refinement (relaxed peak-width)")
    lines.append("")
    lines.append(f"- plot: {chosen_refined_plot_path.as_posix()}")
    lines.append("")
    for sample, candidate, post_result in zip(samples, refined_chosen_sequence["candidates"], post_refinement_results):
        if post_result.get("status") == "ok":
            lines.append(
                f"- {sample['x_label']}: refined Rwp {candidate['rwp']:.2f} | "
                + "; ".join(
                    f"{entry['formula']} {100.0 * entry['weight_fraction']:.1f}%"
                    for entry in candidate.get("formulas", [])
                )
            )
        elif post_result.get("status") == "skipped":
            lines.append(f"- {sample['x_label']}: skipped ({post_result.get('reason', 'no reason provided')})")
        else:
            lines.append(f"- {sample['x_label']}: failed ({post_result.get('error', 'unknown error')})")
    lines.append("")

    lines.append("## Rejected representative sequence")
    lines.append("")
    lines.append(f"- sequence score: {rejected_sequence['score']:.2f}")
    lines.append(f"- chemistry penalty: {rejected_sequence['chemistry_penalty']:.2f}")
    lines.append(f"- continuity score: {rejected_sequence['continuity_score']:.2f}")
    lines.append(f"- plot: {rejected_plot_path.as_posix()}")
    lines.append("")
    for sample, candidate in zip(samples, rejected_sequence["candidates"]):
        lines.append(f"- {sample['x_label']}: {format_candidate_line(candidate)}")
        for reason in rejected_sequence["per_sample_reasons"].get(sample["sample_name"], []):
            lines.append(f"  reason: {reason}")
    for reason in rejected_sequence["transition_reasons"]:
        lines.append(f"- transition issue: {reason}")
    lines.append("")

    lines.append("## Top sequence ranking")
    lines.append("")
    for index, sequence in enumerate(top_sequences, start=1):
        rank_list = ", ".join(str(candidate["rank"]) for candidate in sequence["candidates"])
        lines.append(
            f"- rank {index}: score {sequence['score']:.2f}, chemistry penalty {sequence['chemistry_penalty']:.2f}, continuity score {sequence['continuity_score']:.2f}, candidate ranks [{rank_list}]"
        )
    lines.append("")

    lines.append("## Interpretation")
    lines.append("")
    lines.append("- The ball-milled pattern is most consistent with mostly elemental Se, Ni, and Sn, which is plausible before strong thermal reaction.")
    lines.append("- The 600C and 700C patterns are most self-consistent as a SnSe plus nickel-selenide mixture, with NiSe2 and Ni3Se4 families remaining present across both temperatures.")
    lines.append("- The 800C, 900C, and 1000C patterns move into a second continuous regime dominated by Ni6Se5 plus Ni3Se4 or NiSe2 families, with Sn-bearing selenides reduced to minor fractions.")
    lines.append("- Candidate sequences that reintroduce elemental or non-selenide Ni-Sn phases after heating are penalized because they break the expected ball-mill-to-anneal reaction continuity.")
    lines.append("- Post-selection refinement with relaxed per-phase peak-width ranges was run on the selected sequence; the refined composition plot above should be used as the final fraction reference.")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def write_analysis_json(
    output_path: Path,
    samples: list[dict],
    chosen_sequence: dict,
    refined_chosen_sequence: dict,
    rejected_sequence: dict,
    post_refinement_results: list[dict[str, object]],
    top_sequences: list[dict],
) -> None:
    payload = {
        "samples": [
            {
                "sample_name": sample["sample_name"],
                "run_dir": sample["run_dir"].as_posix(),
                "temperature_c": sample["temperature_c"],
                "x_label": sample["x_label"],
                "best_rwp": sample["best_rwp"],
                "candidates": sample["candidates"],
            }
            for sample in samples
        ],
        "selected_sequence": {
            "score": chosen_sequence["score"],
            "chemistry_penalty": chosen_sequence["chemistry_penalty"],
            "continuity_score": chosen_sequence["continuity_score"],
            "candidate_ranks": [candidate["rank"] for candidate in chosen_sequence["candidates"]],
            "per_sample_reasons": chosen_sequence["per_sample_reasons"],
            "transition_reasons": chosen_sequence["transition_reasons"],
        },
        "selected_sequence_post_refinement": {
            "candidate_ranks": [candidate["rank"] for candidate in refined_chosen_sequence["candidates"]],
            "candidates": refined_chosen_sequence["candidates"],
        },
        "post_refinement_results": post_refinement_results,
        "rejected_sequence": {
            "score": rejected_sequence["score"],
            "chemistry_penalty": rejected_sequence["chemistry_penalty"],
            "continuity_score": rejected_sequence["continuity_score"],
            "candidate_ranks": [candidate["rank"] for candidate in rejected_sequence["candidates"]],
            "per_sample_reasons": rejected_sequence["per_sample_reasons"],
            "transition_reasons": rejected_sequence["transition_reasons"],
        },
        "top_sequence_ranks": [
            {
                "score": sequence["score"],
                "chemistry_penalty": sequence["chemistry_penalty"],
                "continuity_score": sequence["continuity_score"],
                "candidate_ranks": [candidate["rank"] for candidate in sequence["candidates"]],
            }
            for sequence in top_sequences
        ],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze a related series of Dara XRD solutions and rank continuity-consistent sequences.")
    parser.add_argument("--series-dir", type=Path, required=True)
    parser.add_argument("--database", default="COMBINED", choices=["COD", "ICSD", "MP", "ALL", "COMBINED"])
    parser.add_argument(
        "--batch-id",
        default=None,
        help="Batch ID for grouping analysis (e.g., 'batch_001'). If not provided, uses the latest batch or creates batch_001.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    series_dir = args.series_dir.resolve()
    samples = load_series_data(series_dir, args.database)
    sequences = enumerate_sequences(samples)
    chosen_sequence = sequences[0]
    rejected_sequence = choose_rejected_sequence(sequences)

    metadata_root = series_dir / "metadata" / "dara"
    batch_id, batch_dir = find_or_create_batch(metadata_root, args.batch_id)
    analysis_dir = batch_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    
    chosen_plot_path = analysis_dir / "reasonable_sequence.png"
    chosen_refined_plot_path = analysis_dir / "reasonable_sequence_post_refined.png"
    rejected_plot_path = analysis_dir / "rejected_sequence.png"
    render_sequence_plot(
        samples,
        chosen_sequence,
        title="Selected sequence",
        subtitle="continuous selenide evolution with lower penalty",
        output_path=chosen_plot_path,
    )
    render_sequence_plot(
        samples,
        rejected_sequence,
        title="Rejected sequence",
        subtitle="continuity break or chemically implausible heated phases",
        output_path=rejected_plot_path,
    )

    post_refinement_results, refined_chosen_sequence = run_post_selection_refinement(
        samples=samples,
        chosen_sequence=chosen_sequence,
        analysis_dir=analysis_dir,
    )
    render_sequence_plot(
        samples,
        refined_chosen_sequence,
        title="Selected sequence (post-refined)",
        subtitle="relaxed peak-width refinement for selected phase set",
        output_path=chosen_refined_plot_path,
    )

    report_path = analysis_dir / f"series_analysis_report.md"
    top_sequences = sequences[:5]
    write_report(
        series_dir,
        report_path,
        analysis_dir,
        samples,
        chosen_sequence,
        refined_chosen_sequence,
        rejected_sequence,
        chosen_plot_path,
        chosen_refined_plot_path,
        rejected_plot_path,
        post_refinement_results,
        top_sequences,
    )
    write_analysis_json(
        analysis_dir / "series_analysis.json",
        samples,
        chosen_sequence,
        refined_chosen_sequence,
        rejected_sequence,
        post_refinement_results,
        top_sequences,
    )

    print(f"batch_id={batch_id}")
    print(f"batch_dir={batch_dir.as_posix()}")
    print(f"report_path={report_path.as_posix()}")
    print(f"analysis_dir={analysis_dir.as_posix()}")
    print("selected_candidate_ranks=" + ",".join(str(candidate["rank"]) for candidate in chosen_sequence["candidates"]))
    print("rejected_candidate_ranks=" + ",".join(str(candidate["rank"]) for candidate in rejected_sequence["candidates"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())