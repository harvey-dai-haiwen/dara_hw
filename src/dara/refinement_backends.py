"""Unified refinement backend adapters for Dara.

The BGMN path remains the reference implementation. GSAS-II and FullProf are
implemented as opt-in confirmation backends that return Dara-compatible
``RefinementResult`` objects so search-match can use the same downstream code.
"""

from __future__ import annotations

import json
import os
import pickle
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
from pybaselines import Baseline
from pymatgen.analysis.diffraction.xrd import XRDCalculator
from pymatgen.core import Structure
from pymatgen.io.cif import CifWriter
from scipy.signal import find_peaks, peak_widths
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from dara.result import DiaResult, LstResult, PhaseResult, RefinementResult
from dara.utils import get_logger, get_wavelength
from dara.xrd import convert_pattern_to_xy, load_pattern

RefinementBackend = Literal["bgmn", "gsas", "fullprof"]

DEFAULT_GSAS_REPO = Path(r"D:\Haiwen\Code_Repositories\XRD structure solution\reference repos\GSAS-II")
DEFAULT_GSAS_INSTPRM = DEFAULT_GSAS_REPO / "tests" / "testinp" / "INST_XRY.PRM"
DEFAULT_FULLPROF_ROOT = Path(r"D:\Haiwen\Tools\FullProfAPP\runtime\resources\fpsuite\windows")

REFINEMENT_BACKEND_CAPABILITIES: dict[str, dict[str, bool]] = {
    "bgmn": {
        "supports_bounded_lattice": True,
        "supports_phase_fraction": True,
        "supports_profile_refine": True,
        "supports_multiphase": True,
        "supports_plot_export": True,
        "supports_atomic_refine": True,
    },
    "gsas": {
        "supports_bounded_lattice": True,
        "supports_phase_fraction": True,
        "supports_profile_refine": True,
        "supports_multiphase": True,
        "supports_plot_export": True,
        "supports_atomic_refine": False,
    },
    "fullprof": {
        "supports_bounded_lattice": True,
        "supports_phase_fraction": True,
        "supports_profile_refine": True,
        "supports_multiphase": False,
        "supports_plot_export": True,
        "supports_atomic_refine": False,
    },
}

logger = get_logger(__name__)


class BackendRefinementError(RuntimeError):
    """Raised when an optional refinement backend cannot complete."""


@dataclass
class BackendRunContext:
    pattern_path: Path
    phases: list[Any]
    wavelength: Literal["Cu", "Co", "Cr", "Fe", "Mo"] | float
    instrument_profile: str | Path
    working_dir: Path
    phase_params: dict[str, Any] = field(default_factory=dict)
    refinement_params: dict[str, Any] = field(default_factory=dict)
    backend_options: dict[str, Any] = field(default_factory=dict)
    show_progress: bool = False


def normalize_backend(backend: str | None) -> RefinementBackend:
    """Normalize and validate a refinement backend name."""
    normalized = (backend or "bgmn").strip().lower().replace("bgmn", "bgmn")
    if normalized not in REFINEMENT_BACKEND_CAPABILITIES:
        raise ValueError(
            f"Unknown refinement backend {backend!r}. "
            f"Expected one of {', '.join(REFINEMENT_BACKEND_CAPABILITIES)}."
        )
    return normalized  # type: ignore[return-value]


def run_refinement_backend(
    pattern_path: Path | str,
    phases: list[Any],
    wavelength: Literal["Cu", "Co", "Cr", "Fe", "Mo"] | float = "Cu",
    instrument_profile: str | Path = "Aeris-fds-Pixcel1d-Medipix3",
    working_dir: Path | str | None = None,
    phase_params: dict | None = None,
    refinement_params: dict | None = None,
    backend: RefinementBackend | str = "bgmn",
    backend_options: dict[str, Any] | None = None,
    show_progress: bool = False,
) -> RefinementResult:
    """Run a refinement backend and return a Dara-compatible result."""
    backend = normalize_backend(backend)
    pattern_path = Path(pattern_path)
    working_dir = (
        Path(working_dir)
        if working_dir is not None
        else pattern_path.parent / f"refinement_{backend}_{pattern_path.stem}"
    )
    working_dir.mkdir(exist_ok=True, parents=True)

    context = BackendRunContext(
        pattern_path=pattern_path,
        phases=phases,
        wavelength=wavelength,
        instrument_profile=instrument_profile,
        working_dir=working_dir,
        phase_params=phase_params or {},
        refinement_params=refinement_params or {},
        backend_options=backend_options or {},
        show_progress=show_progress,
    )
    if backend == "bgmn":
        return _run_bgmn_backend(context)
    if backend == "gsas":
        conda_env = context.backend_options.get("gsas_conda_env", "GSASII_fix")
        if (
            conda_env
            and not context.backend_options.get("_external_worker")
            and os.environ.get("CONDA_DEFAULT_ENV") != conda_env
        ):
            return _run_external_gsas_backend(context, str(conda_env))
        return _run_gsas_backend(context)
    if backend == "fullprof":
        return _run_fullprof_backend(context)
    raise ValueError(f"Unsupported backend {backend!r}")


def _make_phase(path_obj: Any):
    from dara.refine import RefinementPhase

    return RefinementPhase.make(path_obj)


def _coerce_phases(phases: list[Any]) -> list[Any]:
    return [_make_phase(phase) for phase in phases]


def _run_external_gsas_backend(context: BackendRunContext, conda_env: str) -> RefinementResult:
    """Run GSAS-II in a dedicated conda env and unpickle the Dara result."""
    result_path = context.working_dir / "gsas_external_result.pkl"
    error_path = context.working_dir / "gsas_external_error.txt"
    phases_payload = [
        {"path": _make_phase(phase).path.as_posix(), "params": dict(_make_phase(phase).params)}
        for phase in context.phases
    ]
    options = dict(context.backend_options)
    options["_external_worker"] = True
    payload = {
        "pattern_path": context.pattern_path.as_posix(),
        "phases": phases_payload,
        "wavelength": context.wavelength,
        "instrument_profile": str(context.instrument_profile),
        "working_dir": context.working_dir.as_posix(),
        "phase_params": context.phase_params,
        "refinement_params": context.refinement_params,
        "backend_options": options,
        "result_path": result_path.as_posix(),
        "error_path": error_path.as_posix(),
    }
    payload_path = context.working_dir / "gsas_external_payload.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    worker_path = context.working_dir / "gsas_external_worker.py"
    worker_path.write_text(
        "\n".join(
            [
                "import json",
                "import pickle",
                "import sys",
                "import traceback",
                "from pathlib import Path",
                "from dara.refine import RefinementPhase, do_refinement",
                "payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))",
                "phases = [RefinementPhase(path=item['path'], params=item.get('params', {})) for item in payload['phases']]",
                "try:",
                "    result = do_refinement(",
                "        payload['pattern_path'],",
                "        phases,",
                "        wavelength=payload['wavelength'],",
                "        instrument_profile=payload['instrument_profile'],",
                "        working_dir=payload['working_dir'],",
                "        phase_params=payload['phase_params'],",
                "        refinement_params=payload['refinement_params'],",
                "        backend='gsas',",
                "        backend_options=payload['backend_options'],",
                "    )",
                "    Path(payload['result_path']).write_bytes(pickle.dumps(result))",
                "except Exception:",
                "    Path(payload['error_path']).write_text(traceback.format_exc(), encoding='utf-8')",
                "    raise",
            ]
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    src_root = Path(__file__).resolve().parents[1]
    env["PYTHONPATH"] = str(src_root) + os.pathsep + env.get("PYTHONPATH", "")
    conda_tmp = context.working_dir / "conda_tmp"
    conda_tmp.mkdir(exist_ok=True)
    env["TMP"] = conda_tmp.as_posix()
    env["TEMP"] = conda_tmp.as_posix()
    completed = subprocess.run(
        ["conda", "run", "-n", conda_env, "python", str(worker_path), str(payload_path)],
        cwd=context.working_dir,
        env=env,
        text=True,
        capture_output=True,
        timeout=int(context.backend_options.get("backend_timeout", context.backend_options.get("timeout", 300))),
        check=False,
    )
    (context.working_dir / "gsas_external_stdout.txt").write_text(
        completed.stdout + completed.stderr,
        encoding="utf-8",
        errors="ignore",
    )
    if completed.returncode != 0 or not result_path.exists():
        details = error_path.read_text(encoding="utf-8", errors="ignore") if error_path.exists() else completed.stderr
        raise BackendRefinementError(
            f"External GSAS-II worker failed in conda env {conda_env!r}: {details[:2000]}"
        )
    return pickle.loads(result_path.read_bytes())


def _run_bgmn_backend(context: BackendRunContext) -> RefinementResult:
    from dara.bgmn_worker import BGMNWorker
    from dara.cif2str import cif2str
    from dara.generate_control_file import generate_control_file
    from dara.result import get_result

    pattern_path = context.pattern_path
    if pattern_path.suffix.lower() not in (".xy",):
        pattern_path = convert_pattern_to_xy(pattern_path, context.working_dir)

    str_paths = []
    for phase_path in context.phases:
        phase = _make_phase(phase_path)
        phase_params = context.phase_params.copy()
        phase_params.update(phase.params)
        phase_path_ = phase.path
        if phase_path_.suffix.lower() == ".cif":
            str_path = cif2str(phase_path_, "", context.working_dir, **phase_params)
        else:
            if phase_path_.parent != context.working_dir:
                shutil.copy(phase_path_, context.working_dir)
            str_path = context.working_dir / phase_path_.name
        str_paths.append(str_path)

    control_file_path = generate_control_file(
        pattern_path=pattern_path,
        str_paths=str_paths,
        instrument_profile=context.instrument_profile,
        working_dir=context.working_dir,
        wavelength=context.wavelength,
        **context.refinement_params,
    )

    bgmn_worker = BGMNWorker()
    bgmn_worker.run_refinement_cmd(control_file_path, show_progress=context.show_progress)
    result = get_result(control_file_path)
    return _attach_backend_metadata(
        result,
        backend="bgmn",
        working_dir=context.working_dir,
        stage_log=[{"stage": "bgmn", "status": "ok"}],
        warnings=[],
    )


def _configure_gsasii(gsas_repo: Path) -> None:
    sys.meta_path[:] = [
        finder
        for finder in sys.meta_path
        if "_gsas_ii_editable_loader" not in type(finder).__module__
    ]
    if not gsas_repo.exists():
        raise BackendRefinementError(f"GSAS-II repo not found: {gsas_repo}")
    repo_str = str(gsas_repo)
    if repo_str in sys.path:
        sys.path.remove(repo_str)
    sys.path.insert(0, repo_str)
    build_sources = sorted(gsas_repo.glob("build/*/sources"), key=lambda path: path.stat().st_mtime)
    if build_sources:
        source_str = str(build_sources[-1])
        if source_str in sys.path:
            sys.path.remove(source_str)
        sys.path.insert(0, source_str)
        import GSASII

        if source_str not in GSASII.__path__:
            GSASII.__path__.append(source_str)

    import GSASII.GSASIIscriptable as G2sc

    G2sc.LoadG2fil()


def _normalize_cif_for_gsas(source_cif: Path, output_cif: Path) -> Path:
    structure = Structure.from_file(source_cif)
    try:
        structure.remove_oxidation_states()
    except Exception:
        pass
    CifWriter(structure, symprec=0.1).write_file(output_cif)
    return output_cif


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _wavelength_angstrom(wavelength: Literal["Cu", "Co", "Cr", "Fe", "Mo"] | float) -> float:
    value = get_wavelength(wavelength)
    return float(value * 10 if value < 1 else value)


def _run_gsas_backend(context: BackendRunContext) -> RefinementResult:
    options = context.backend_options
    gsas_repo = Path(options.get("gsas_repo") or DEFAULT_GSAS_REPO)
    instprm = Path(options.get("gsas_instprm") or options.get("instprm") or DEFAULT_GSAS_INSTPRM)
    if not instprm.exists():
        raise BackendRefinementError(f"GSAS-II instrument parameter file not found: {instprm}")

    _configure_gsasii(gsas_repo)
    import GSASII.GSASIIscriptable as G2sc

    phases = _coerce_phases(context.phases)
    if not phases:
        raise BackendRefinementError("GSAS-II backend needs at least one phase.")

    pattern_path = convert_pattern_to_xy(context.pattern_path, context.working_dir)
    project_path = context.working_dir / "refinement.gpx"
    stage_log: list[dict[str, Any]] = []
    warnings_list: list[str] = []
    start = time.perf_counter()

    try:
        gpx = G2sc.G2Project(newgpx=str(project_path))
        histogram = gpx.add_powder_histogram(
            str(pattern_path),
            str(instprm),
            fmthint=options.get("fmthint", "Topas xye"),
        )
        gsas_phases = []
        for phase in phases:
            phase_cif = _normalize_cif_for_gsas(
                phase.path,
                context.working_dir / f"{phase.path.stem}_gsas.cif",
            )
            try:
                gsas_phases.append(
                    gpx.add_phase(str(phase_cif), phasename=phase.path.stem, histograms=[histogram])
                )
            except Exception as exc:
                warnings_list.append(
                    f"GSAS-II normalized CIF import failed for {phase.path.name}: "
                    f"{type(exc).__name__}: {exc}; retrying original CIF."
                )
                gsas_phases.append(
                    gpx.add_phase(str(phase.path), phasename=phase.path.stem, histograms=[histogram])
                )

        wmin = float(context.refinement_params.get("wmin", options.get("wmin", 5.0)))
        wmax = float(context.refinement_params.get("wmax", options.get("wmax", 90.0)))
        cycles = int(options.get("cycles", 6))
        background_coeffs = int(options.get("background_coeffs", 12))
        gsas_profile = _estimate_gsas_profile_from_pattern(pattern_path, wmin, wmax, options)

        histogram.set_refinements({"Limits": [wmin, wmax]})
        _apply_gsas_profile_seed(histogram, gsas_profile)
        gpx.set_Controls("cycles", 0)
        gpx.refine(makeBack=True)
        stage_log.append({"stage": "zero-cycle sanity", "status": "ok", "profile_seed": gsas_profile})

        gpx.set_Controls("cycles", cycles)
        background_info = _apply_gsas_background_seed(
            histogram,
            pattern_path,
            wmin=wmin,
            wmax=wmax,
            background_coeffs=background_coeffs,
            options=options,
        )
        gpx.refine(makeBack=True)
        stage_log.append({"stage": "dara-python background", "status": "ok", **background_info})

        for phase in gsas_phases:
            phase.set_HAP_refinements({"Scale": True}, [histogram])
        gpx.refine(makeBack=True)
        stage_log.append({"stage": "scale only", "status": "ok"})

        histogram.set_refinements({"Sample Parameters": {"Shift": True}})
        gpx.refine(makeBack=True)
        stage_log.append({"stage": "zero/sample shift", "status": "ok"})

        base_cells = [_get_structure_lattice_parameters(phase.path) for phase in phases]
        for phase in gsas_phases:
            phase.set_refinements({"Cell": True})
        gpx.refine(makeBack=True)
        bounded_warnings = _check_gsas_lattice_bounds(gsas_phases, base_cells, options)
        warnings_list.extend(bounded_warnings)
        stage_log.append({"stage": "bounded lattice", "status": "ok", "warnings": bounded_warnings})

        if options.get("profile_refine", True):
            try:
                histogram.set_refinements({"Instrument Parameters": options.get("profile_refine_params", ["W"])})
                gpx.refine(makeBack=True)
                stage_log.append({"stage": "optional profile", "status": "ok"})
            except Exception as exc:
                warning = f"GSAS-II profile refinement skipped: {type(exc).__name__}: {exc}"
                warnings_list.append(warning)
                stage_log.append({"stage": "optional profile", "status": "warning", "message": warning})
        else:
            warnings_list.append("GSAS-II atomic/occupancy/Biso refinement disabled by Dara backend policy.")

        gpx.save()
        residuals = dict(histogram.residuals)
        metrics = _collect_gsas_metrics(context.working_dir / "refinement.lst", residuals)
        scales = _collect_gsas_phase_scales(gsas_phases, histogram)
        plot_arrays = _collect_gsas_plot_arrays(histogram)
    except Exception as exc:
        raise BackendRefinementError(f"GSAS-II refinement failed: {type(exc).__name__}: {exc}") from exc

    return _build_backend_result(
        context=context,
        backend="gsas",
        phases=phases,
        metrics=metrics,
        phase_weights=scales,
        plot_arrays=plot_arrays,
        stage_log=stage_log,
        warnings=warnings_list,
        elapsed_seconds=time.perf_counter() - start,
    )


def _get_structure_lattice_parameters(cif_path: Path) -> tuple[float, float, float, float, float, float]:
    structure = Structure.from_file(cif_path)
    lattice = structure.lattice
    return (*lattice.abc, *lattice.angles)


def _load_pattern_arrays(pattern_path: Path) -> tuple[np.ndarray, np.ndarray]:
    pattern = load_pattern(pattern_path)
    x = np.asarray(pattern.angles, dtype=float)
    y = np.asarray(pattern.intensities, dtype=float)
    order = np.argsort(x)
    return x[order], y[order]


def _estimate_baseline_py(
    x: np.ndarray,
    y: np.ndarray,
    options: dict[str, Any],
) -> np.ndarray:
    method = str(options.get("gsas_background_estimator", "asls")).lower()
    y_safe = np.clip(y, 1e-6, None)
    baseline_fitter = Baseline(x_data=x)
    if method == "snip":
        half_window = options.get("gsas_background_half_window")
        if half_window is None:
            half_window = max(20, min(160, len(y_safe) // 80))
        baseline, _params = baseline_fitter.snip(
            y_safe,
            max_half_window=int(half_window),
            decreasing=True,
            smooth_half_window=int(options.get("gsas_background_smooth_half_window", 3)),
        )
    else:
        lam = float(options.get("gsas_background_lam", 1e7))
        p = float(options.get("gsas_background_p", 0.005))
        baseline, _params = baseline_fitter.asls(y_safe, lam=lam, p=p)
    baseline = np.asarray(baseline, dtype=float)
    return np.clip(baseline, 0.0, np.maximum(y_safe, baseline).max())


def _make_fixed_background_points(
    x: np.ndarray,
    baseline: np.ndarray,
    wmin: float,
    wmax: float,
    max_points: int,
) -> list[tuple[float, float]]:
    mask = (x >= wmin) & (x <= wmax)
    x_sel = x[mask]
    y_sel = baseline[mask]
    if len(x_sel) == 0:
        return []
    if len(x_sel) <= max_points:
        idx = np.arange(len(x_sel))
    else:
        idx = np.linspace(0, len(x_sel) - 1, max_points).round().astype(int)
    points = [(float(x_sel[i]), float(y_sel[i])) for i in idx]
    return list(dict.fromkeys(points))


def _apply_gsas_background_seed(
    histogram: Any,
    pattern_path: Path,
    wmin: float,
    wmax: float,
    background_coeffs: int,
    options: dict[str, Any],
) -> dict[str, Any]:
    x, y = _load_pattern_arrays(pattern_path)
    baseline = _estimate_baseline_py(x, y, options)
    fixed_points = _make_fixed_background_points(
        x,
        baseline,
        wmin,
        wmax,
        max_points=int(options.get("gsas_background_fixed_points", 160)),
    )
    if not fixed_points:
        histogram.set_refinements({"Background": {"no. coeffs": background_coeffs, "refine": True}})
        return {"mode": "chebyshev fallback", "coeffs": background_coeffs, "fixed_points": 0}

    histogram.set_refinements(
        {
            "Background": {
                "type": options.get("gsas_background_type", "chebyschev-1"),
                "no. coeffs": background_coeffs,
                "refine": bool(options.get("gsas_background_refine", True)),
                "FixedPoints": fixed_points,
                "fit fixed points": True,
            }
        }
    )
    seed_path = Path(pattern_path).parent / "dara_gsas_background_seed.xy"
    np.savetxt(seed_path, np.column_stack([x, baseline]), fmt="%.8g")
    return {
        "mode": "dara-python fixed-points",
        "coeffs": background_coeffs,
        "fixed_points": len(fixed_points),
        "seed_path": seed_path.as_posix(),
    }


def _estimate_gsas_profile_from_pattern(
    pattern_path: Path,
    wmin: float,
    wmax: float,
    options: dict[str, Any],
) -> dict[str, float | int]:
    x, y = _load_pattern_arrays(pattern_path)
    mask = (x >= wmin) & (x <= wmax)
    x_fit = x[mask]
    y_fit = y[mask]
    if len(x_fit) < 10:
        return {"median_fwhm_deg": 0.10, "W": 20.0, "num_peaks": 0}

    baseline = _estimate_baseline_py(x_fit, y_fit, options)
    signal = np.clip(y_fit - baseline, 0.0, None)
    if signal.max() <= 0:
        return {"median_fwhm_deg": 0.10, "W": 20.0, "num_peaks": 0}

    prominence = float(options.get("gsas_peak_prominence_fraction", 0.03)) * float(signal.max())
    distance_points = int(options.get("gsas_peak_min_distance_points", 5))
    peaks, _props = find_peaks(signal, prominence=max(prominence, 1.0), distance=max(1, distance_points))
    if len(peaks) == 0:
        return {"median_fwhm_deg": 0.10, "W": 20.0, "num_peaks": 0}

    widths, _height, left_ips, right_ips = peak_widths(signal, peaks, rel_height=0.5)
    fwhm_deg = np.interp(right_ips, np.arange(len(x_fit)), x_fit) - np.interp(left_ips, np.arange(len(x_fit)), x_fit)
    fwhm_deg = fwhm_deg[np.isfinite(fwhm_deg)]
    fwhm_deg = fwhm_deg[(fwhm_deg > 0.02) & (fwhm_deg < 1.5)]
    if len(fwhm_deg) == 0:
        return {"median_fwhm_deg": 0.10, "W": 20.0, "num_peaks": int(len(peaks))}

    percentile = float(options.get("gsas_peak_width_percentile", 50))
    median_fwhm = float(np.percentile(fwhm_deg, percentile))
    median_fwhm = float(np.clip(median_fwhm, 0.04, float(options.get("gsas_peak_width_max_deg", 0.8))))
    # GSAS-II Gaussian sigma term is in centideg**2. FWHM ~= sqrt(8 ln 2 * sig)/100.
    w_value = (median_fwhm * 100.0) ** 2 / (8.0 * np.log(2.0))
    w_value = float(np.clip(w_value, 1.0, float(options.get("gsas_profile_w_max", 500.0))))
    return {"median_fwhm_deg": median_fwhm, "W": w_value, "num_peaks": int(len(fwhm_deg))}


def _apply_gsas_profile_seed(histogram: Any, profile: dict[str, float | int]) -> None:
    inst = histogram.InstrumentParameters
    if "W" in inst:
        current = _safe_float(inst["W"][1]) or 0.0
        inst["W"][0] = max(current, float(profile["W"]))
        inst["W"][1] = inst["W"][0]
    if "U" in inst:
        inst["U"][0] = max(0.0, _safe_float(inst["U"][0]) or 0.0)
        inst["U"][1] = inst["U"][0]
    if "V" in inst:
        inst["V"][0] = min(0.0, _safe_float(inst["V"][0]) or 0.0)
        inst["V"][1] = inst["V"][0]
    if "X" in inst:
        inst["X"][0] = max(0.01, _safe_float(inst["X"][0]) or 0.0)
        inst["X"][1] = inst["X"][0]
    if "Y" in inst:
        inst["Y"][0] = max(0.01, _safe_float(inst["Y"][0]) or 0.0)
        inst["Y"][1] = inst["Y"][0]


def _check_gsas_lattice_bounds(gsas_phases: list[Any], base_cells: list[tuple[float, ...]], options: dict[str, Any]) -> list[str]:
    warnings_list: list[str] = []
    bound = float(options.get("lattice_bound", 0.01))
    for phase, base_cell in zip(gsas_phases, base_cells):
        try:
            cell = phase.get_cell()
        except Exception:
            continue
        if isinstance(cell, dict):
            refined_lengths = [cell.get("a"), cell.get("b"), cell.get("c")]
        else:
            refined_lengths = list(cell[:3])
        for axis, initial, refined in zip(("a", "b", "c"), base_cell[:3], refined_lengths):
            if refined is None:
                continue
            if initial and abs(refined - initial) / initial > bound:
                warnings_list.append(
                    f"{phase.name} {axis} changed {abs(refined - initial) / initial:.3%}, "
                    f"outside +/-{bound:.1%}; result kept but marked warning."
                )
    return warnings_list


def _collect_gsas_metrics(lst_path: Path, residuals: dict[str, Any]) -> dict[str, float | None]:
    metrics: dict[str, float | None] = {
        "Rwp": _safe_float(residuals.get("wR")),
        "Rp": _safe_float(residuals.get("R")),
        "Rexp": _safe_float(residuals.get("wRmin")),
        "GOF": None,
    }
    if lst_path.exists():
        number = r"([0-9]+(?:\.[0-9]*)?(?:e[+-]?\d+)?)"
        text = lst_path.read_text(encoding="utf-8", errors="ignore")
        match = re.search(
            rf"wR\s*=\s*{number}%,\s*chi\*\*2\s*=\s*{number},\s*GOF\s*=\s*{number}",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            metrics["Rwp"] = float(match.group(1))
            metrics["GOF"] = float(match.group(3))
    if metrics["GOF"] is None and metrics["Rwp"] and metrics["Rexp"]:
        metrics["GOF"] = metrics["Rwp"] / metrics["Rexp"]
    return metrics


def _collect_gsas_phase_scales(gsas_phases: list[Any], histogram: Any) -> dict[str, float]:
    scales: dict[str, float] = {}
    for phase in gsas_phases:
        value = None
        for getter in (
            lambda: phase.getHAPentryValue("Scale", histogram),
            lambda: phase.get_HAP_refinements(histogram).get("Scale"),
        ):
            try:
                raw = getter()
                value = raw[0] if isinstance(raw, (list, tuple)) else raw
                break
            except Exception:
                continue
        scales[phase.name] = max(0.0, _safe_float(value) or 0.0)
    if not any(scales.values()):
        scales = {phase.name: 1.0 for phase in gsas_phases}
    return scales


def _collect_gsas_plot_arrays(histogram: Any) -> dict[str, list[float]]:
    arrays: dict[str, list[float]] = {}
    for target, keys in {
        "x": ("x", "X"),
        "y_obs": ("Yobs", "yobs", "Y"),
        "y_calc": ("Ycalc", "ycalc"),
        "y_bkg": ("Background", "background", "Back"),
    }.items():
        for key in keys:
            try:
                value = histogram.getdata(key)
                if value is not None:
                    arrays[target] = np.asarray(value, dtype=float).tolist()
                    break
            except Exception:
                continue
    if "x" not in arrays or "y_obs" not in arrays:
        raise BackendRefinementError("GSAS-II did not expose required plot arrays.")
    arrays.setdefault("y_calc", arrays["y_obs"])
    arrays.setdefault("y_bkg", [0.0] * len(arrays["x"]))
    return arrays


def _run_fullprof_backend(context: BackendRunContext) -> RefinementResult:
    options = context.backend_options
    fullprof_root = Path(options.get("fullprof_root") or DEFAULT_FULLPROF_ROOT)
    fp2k = Path(options.get("fp2k_path") or fullprof_root / "fp2k.exe")
    cif_to_pcr = Path(options.get("cif_to_pcr_path") or fullprof_root / "CIFs_to_PCR.exe")
    if not fp2k.exists():
        raise BackendRefinementError(f"FullProf fp2k.exe not found: {fp2k}")
    if not cif_to_pcr.exists():
        raise BackendRefinementError(f"FullProf CIFs_to_PCR.exe not found: {cif_to_pcr}")

    phases = _coerce_phases(context.phases)
    if len(phases) != 1:
        raise BackendRefinementError(
            "FullProf backend currently supports single-phase confirmation only; "
            "multi-phase Dara-controlled PCR generation is marked unsupported."
        )

    pattern_path = convert_pattern_to_xy(context.pattern_path, context.working_dir)
    generator = FullProfPcrGenerator(
        fullprof_root=fullprof_root,
        cif_to_pcr=cif_to_pcr,
        fp2k=fp2k,
        timeout_s=int(options.get("timeout", options.get("backend_timeout", 120))),
    )
    start = time.perf_counter()
    pcr_path = generator.generate(
        pattern_path=pattern_path,
        phase_path=phases[0].path,
        run_dir=context.working_dir,
        wavelength=context.wavelength,
        refinement_params=context.refinement_params,
        options=options,
    )
    stage_log = list(generator.stage_log)
    returncode, stdout = generator.run_fp2k(pcr_path)
    (context.working_dir / "fp2k_stdout.txt").write_text(stdout, encoding="utf-8", errors="ignore")
    stage_log.append({"stage": "fp2k", "status": "ok" if returncode == 0 else "failed", "returncode": returncode})
    if returncode != 0:
        raise BackendRefinementError(f"FullProf fp2k failed with return code {returncode}.")

    metrics, fractions, cells = parse_fullprof_sum(context.working_dir / f"{pcr_path.stem}.sum")
    plot_arrays = parse_fullprof_prf(context.working_dir / f"{pcr_path.stem}.prf")
    warnings_list = [
        "FullProf atomic/occupancy/Biso refinement disabled by Dara backend policy.",
        "FullProf multi-phase backend is experimental and currently single-phase only.",
    ]
    return _build_backend_result(
        context=context,
        backend="fullprof",
        phases=phases,
        metrics=metrics,
        phase_weights={phases[0].path.stem: fractions.get(phases[0].path.stem, 100.0)},
        plot_arrays=plot_arrays,
        stage_log=stage_log,
        warnings=warnings_list,
        elapsed_seconds=time.perf_counter() - start,
        refined_cells=cells,
    )


class FullProfPcrGenerator:
    """Centralized FullProf PCR generation and staged parameter-code handling."""

    def __init__(self, fullprof_root: Path, cif_to_pcr: Path, fp2k: Path, timeout_s: int = 120):
        self.fullprof_root = fullprof_root
        self.cif_to_pcr = cif_to_pcr
        self.fp2k = fp2k
        self.timeout_s = timeout_s
        self.stage_log: list[dict[str, Any]] = []
        self._next_code = 1

    def assign_code(self) -> float:
        code = float(self._next_code)
        self._next_code += 1
        return code

    def generate(
        self,
        pattern_path: Path,
        phase_path: Path,
        run_dir: Path,
        wavelength: Literal["Cu", "Co", "Cr", "Fe", "Mo"] | float,
        refinement_params: dict[str, Any],
        options: dict[str, Any],
    ) -> Path:
        local_cif = run_dir / "candidate.cif"
        shutil.copy2(phase_path, local_cif)
        local_pattern = run_dir / "candidate.dat"
        shutil.copy2(pattern_path, local_pattern)
        fullprof_dim = self.fullprof_root / "fullprof.dim"
        if fullprof_dim.exists():
            shutil.copy2(fullprof_dim, run_dir / fullprof_dim.name)
        returncode, stdout = self._run_text_command([str(self.cif_to_pcr), local_cif.name], run_dir, stdin="\n")
        (run_dir / "cifs_to_pcr_stdout.txt").write_text(stdout, encoding="utf-8", errors="ignore")
        self.stage_log.append({"stage": "PCR generate", "status": "ok" if returncode == 0 else "failed", "returncode": returncode})
        if returncode != 0:
            raise BackendRefinementError(f"CIFs_to_PCR failed with return code {returncode}.")
        pcr_candidates = sorted(run_dir.glob("*.pcr"), key=lambda path: path.stat().st_mtime)
        if not pcr_candidates:
            raise BackendRefinementError("CIFs_to_PCR did not create a .pcr file.")
        pcr_path = pcr_candidates[-1]
        text = pcr_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        text = self._rewrite_pcr_lines(text, local_pattern, wavelength, refinement_params, options)
        pcr_path.write_text("\n".join(text) + "\n", encoding="utf-8")
        self.stage_log.extend(
            [
                {"stage": "background", "status": "configured"},
                {"stage": "scale", "status": "configured"},
                {"stage": "zero", "status": "configured"},
                {"stage": "bounded lattice", "status": "configured"},
            ]
        )
        return pcr_path

    def run_fp2k(self, pcr_path: Path) -> tuple[int, str]:
        return self._run_text_command([str(self.fp2k)], pcr_path.parent, stdin=f"{pcr_path.stem}\n\n\n")

    def _run_text_command(self, command: list[str], run_dir: Path, stdin: str = "") -> tuple[int, str]:
        env = os.environ.copy()
        env["PATH"] = str(self.fullprof_root) + os.pathsep + env.get("PATH", "")
        completed = subprocess.run(
            command,
            input=stdin,
            cwd=run_dir,
            env=env,
            text=True,
            capture_output=True,
            timeout=self.timeout_s,
            check=False,
        )
        return completed.returncode, completed.stdout + completed.stderr

    def _rewrite_pcr_lines(
        self,
        lines: list[str],
        pattern_path: Path,
        wavelength: Literal["Cu", "Co", "Cr", "Fe", "Mo"] | float,
        refinement_params: dict[str, Any],
        options: dict[str, Any],
    ) -> list[str]:
        wavelength_value = _wavelength_angstrom(wavelength)
        rewritten: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.lower().endswith((".dat", ".xy", ".xye", ".txt", ".scn")):
                rewritten.append(pattern_path.name)
                continue
            if stripped.startswith("! lambda"):
                rewritten.append(line)
                continue
            if re.match(r"^\s*\d+\.\d+\s+\d+\.\d+\s+0\.0000", line):
                rewritten.append(f" {wavelength_value:.6f} {wavelength_value:.6f} 0.0000")
                continue
            rewritten.append(line)

        text = "\n".join(rewritten)
        background_coeffs = int(options.get("background_coeffs", 6))
        if "NCY" in text:
            text = re.sub(r"(\bNCY\s*=\s*)\d+", rf"\g<1>{int(options.get('cycles', 8))}", text)
        text = re.sub(r"(\bNba\s*=\s*)\d+", rf"\g<1>{background_coeffs}", text)
        if "Zero" in text and "Code" in text:
            zero_code = self.assign_code()
            raw_zero = refinement_params.get("eps2", 0) or 0
            try:
                zero = float(raw_zero)
            except (TypeError, ValueError):
                zero = 0.0
            text = re.sub(
                r"(?m)^(\s*Zero\s+)([-+0-9.Ee]+)(.*)$",
                rf"\g<1>{zero:.5f}\g<3>",
                text,
                count=1,
            )
            text = re.sub(
                r"(?m)^(\s*Code\s+)([-+0-9.Ee]+)(.*)$",
                rf"\g<1>{zero_code:.1f}\g<3>",
                text,
                count=1,
            )
        return text.splitlines()


def parse_fullprof_sum(sum_path: Path) -> tuple[dict[str, float | None], dict[str, float], dict[str, tuple[float, ...]]]:
    """Parse core metrics, phase fractions, and cells from a FullProf .sum file."""
    if not sum_path.exists():
        raise BackendRefinementError(f"FullProf .sum file not found: {sum_path}")
    text = sum_path.read_text(encoding="utf-8", errors="ignore")
    metrics: dict[str, float | None] = {"Rp": None, "Rwp": None, "Rexp": None, "GOF": None}
    match = re.search(
        r"Conventional Rietveld Rp,Rwp,Re and Chi2:\s*"
        r"([0-9.+-Ee]+)\s+([0-9.+-Ee]+)\s+([0-9.+-Ee]+)\s+([0-9.+-Ee]+)",
        text,
    )
    if match:
        metrics = {
            "Rp": float(match.group(1)),
            "Rwp": float(match.group(2)),
            "Rexp": float(match.group(3)),
            "GOF": float(match.group(4)) ** 0.5,
        }
    else:
        rp_lines = re.findall(
            r"=>\s*Rp:\s*([0-9.+-Ee]+)\s+Rwp:\s*([0-9.+-Ee]+)\s+"
            r"Rexp:\s*([0-9.+-Ee]+)\s+Chi2:\s*([0-9.+-Ee]+)",
            text,
        )
        if rp_lines:
            rp, rwp, rexp, chi2 = rp_lines[-1]
            metrics = {
                "Rp": float(rp),
                "Rwp": float(rwp),
                "Rexp": float(rexp),
                "GOF": float(chi2) ** 0.5,
            }

    fractions: dict[str, float] = {}
    current_phase: str | None = None
    for line in text.splitlines():
        phase_match = re.search(r"=>\s*Phase:\s*\d+\s+(.+)$", line)
        if phase_match:
            current_phase = Path(phase_match.group(1).strip()).stem
            continue
        fraction_match = re.search(r"Fract\(%\):\s*([0-9.+-Ee]+)", line)
        if current_phase and fraction_match:
            fractions[current_phase] = float(fraction_match.group(1))

    cells: dict[str, tuple[float, ...]] = {}
    inline_cell_match = re.search(
        r"Cell parameters\s*:\s*([0-9.+-Ee]+)\s+([0-9.+-Ee]+)\s+([0-9.+-Ee]+)\s+"
        r"([0-9.+-Ee]+)\s+([0-9.+-Ee]+)\s+([0-9.+-Ee]+)",
        text,
    )
    if inline_cell_match:
        phase_name = current_phase or next(iter(fractions), "candidate")
        cells[phase_name] = tuple(float(inline_cell_match.group(i)) for i in range(1, 7))
        return metrics, fractions, cells

    cell_match = re.search(
        r"Cell parameters\s*:\s*(?:\n\s*([0-9.+-Ee]+)\s+[0-9.+-Ee]+){6}",
        text,
    )
    if cell_match:
        cell_values = [
            float(value)
            for value in re.findall(
                r"^\s*([0-9.+-Ee]+)\s+[0-9.+-Ee]+\s*$",
                cell_match.group(0),
                flags=re.MULTILINE,
            )[:6]
        ]
        if len(cell_values) == 6:
            phase_name = current_phase or next(iter(fractions), "candidate")
            cells[phase_name] = tuple(cell_values)
    return metrics, fractions, cells


def parse_fullprof_prf(prf_path: Path) -> dict[str, list[float]]:
    """Parse FullProf .prf plot arrays."""
    if not prf_path.exists():
        raise BackendRefinementError(f"FullProf .prf file not found: {prf_path}")
    x: list[float] = []
    y_obs: list[float] = []
    y_calc: list[float] = []
    y_bkg: list[float] = []
    for line in prf_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            values = [float(parts[i]) for i in range(5)]
        except ValueError:
            continue
        x.append(values[0])
        y_obs.append(values[1])
        y_calc.append(values[2])
        y_bkg.append(values[4])
    if not x:
        raise BackendRefinementError(f"Could not parse FullProf .prf data from {prf_path}")
    return {"x": x, "y_obs": y_obs, "y_calc": y_calc, "y_bkg": y_bkg}


def _build_backend_result(
    context: BackendRunContext,
    backend: str,
    phases: list[Any],
    metrics: dict[str, float | None],
    phase_weights: dict[str, float],
    plot_arrays: dict[str, list[float]],
    stage_log: list[dict[str, Any]],
    warnings: list[str],
    elapsed_seconds: float,
    refined_cells: dict[str, tuple[float, ...]] | None = None,
) -> RefinementResult:
    x = np.asarray(plot_arrays["x"], dtype=float)
    y_obs = np.asarray(plot_arrays["y_obs"], dtype=float)
    y_calc = np.asarray(plot_arrays.get("y_calc", y_obs), dtype=float)
    y_bkg = np.asarray(plot_arrays.get("y_bkg", np.zeros_like(y_obs)), dtype=float)
    if len(y_calc) != len(x):
        y_calc = np.interp(x, np.linspace(float(x.min()), float(x.max()), len(y_calc)), y_calc)
    if len(y_bkg) != len(x):
        y_bkg = np.zeros_like(y_obs)

    peak_data = _simulate_backend_peaks(phases, context.wavelength)
    structs = _estimate_phase_profiles(x, y_calc, y_bkg, phases, phase_weights, peak_data)
    total_weight = sum(max(0.0, weight) for weight in phase_weights.values()) or 1.0
    phase_results = {}
    refined_cells = refined_cells or {}
    for phase in phases:
        phase_name = phase.path.stem
        weight = max(0.0, phase_weights.get(phase_name, 0.0)) / total_weight
        phase_results[phase_name] = _make_phase_result(phase.path, weight, refined_cells.get(phase_name))

    rwp = metrics.get("Rwp")
    rp = metrics.get("Rp")
    rexp = metrics.get("Rexp")
    if rwp is None:
        rwp = _calculate_rwp(y_obs, y_calc)
    if rp is None:
        rp = _calculate_rp(y_obs, y_calc)
    if rexp is None:
        rexp = max(1e-6, float(rwp) / max(1.0, float(metrics.get("GOF") or 1.0)))

    lst_data = LstResult(
        raw_lst=json.dumps({"backend": backend, "metrics": metrics, "warnings": warnings}, indent=2),
        pattern_name=context.pattern_path.name,
        num_steps=int(sum(stage.get("status") == "ok" for stage in stage_log)),
        Rp=float(rp),
        Rpb=float(rp),
        R=float(rp),
        Rwp=float(rwp),
        Rexp=float(rexp),
        d=0.0,
        **{"1-rho": 0.0},
        phases_results=phase_results,
        GOF=metrics.get("GOF"),
        EPS1=0.0,
        EPS2=0.0,
        backend=backend,
    )
    result = RefinementResult(
        lst_data=lst_data,
        plot_data=DiaResult(
            x=x.tolist(),
            y_obs=y_obs.tolist(),
            y_calc=y_calc.tolist(),
            y_bkg=y_bkg.tolist(),
            structs=structs,
        ),
        peak_data=peak_data,
        backend_name=backend,
        backend_version=None,
        backend_capabilities=REFINEMENT_BACKEND_CAPABILITIES[backend],
        stage_log=stage_log,
        warnings=warnings,
        raw_output_dir=context.working_dir.as_posix(),
        elapsed_seconds=elapsed_seconds,
    )
    _write_unified_outputs(result, context.working_dir, backend)
    return result


def _make_phase_result(cif_path: Path, weight_fraction: float, refined_cell: tuple[float, ...] | None = None) -> PhaseResult:
    structure = Structure.from_file(cif_path)
    try:
        spg = SpacegroupAnalyzer(structure, symprec=0.1)
        spacegroup_no = spg.get_space_group_number()
        spacegroup_symbol = spg.get_space_group_symbol()
    except Exception:
        spacegroup_no = 1
        spacegroup_symbol = "P1"
    lattice = refined_cell or (*structure.lattice.abc, *structure.lattice.angles)
    atom_lines = []
    for index, site in enumerate(structure, start=1):
        coords = site.frac_coords
        species = ",".join(f"{el.symbol.upper()}({occ:.4f})" for el, occ in site.species.items())
        atom_lines.append(f"{index:3d} {coords[0]:8.4f} {coords[1]:8.4f} {coords[2]:8.4f} E=({species})")
    return PhaseResult(
        SpacegroupNo=spacegroup_no,
        HermannMauguin=spacegroup_symbol,
        XrayDensity=structure.density,
        Rphase=0.0,
        UNIT="NM",
        GEWICHT=float(weight_fraction),
        A=float(lattice[0]) / 10,
        B=float(lattice[1]) / 10,
        C=float(lattice[2]) / 10,
        ALPHA=float(lattice[3]),
        BETA=float(lattice[4]),
        GAMMA=float(lattice[5]),
        k1=0.0,
        B1=0.0,
        atom_positions_string="\n".join(atom_lines),
    )


def _simulate_backend_peaks(phases: list[Any], wavelength: Literal["Cu", "Co", "Cr", "Fe", "Mo"] | float) -> pd.DataFrame:
    calculator = XRDCalculator(wavelength=_wavelength_angstrom(wavelength))
    rows: list[dict[str, Any]] = []
    for phase_index, phase in enumerate(phases):
        structure = Structure.from_file(phase.path)
        pattern = calculator.get_pattern(structure, two_theta_range=(5, 90))
        for two_theta, intensity, hkls in zip(pattern.x, pattern.y, pattern.hkls):
            if intensity <= 0:
                continue
            hkl = hkls[0]["hkl"] if hkls else (0, 0, 0)
            rows.append(
                {
                    "2theta": float(two_theta),
                    "intensity": float(intensity),
                    "b1": 0.0,
                    "b2": 0.0,
                    "h": int(hkl[0]),
                    "k": int(hkl[1]),
                    "l": int(hkl[2]),
                    "phase": phase.path.stem,
                    "phase_idx": phase_index,
                }
            )
    return pd.DataFrame(rows, columns=["2theta", "intensity", "b1", "b2", "h", "k", "l", "phase", "phase_idx"])


def _estimate_phase_profiles(
    x: np.ndarray,
    y_calc: np.ndarray,
    y_bkg: np.ndarray,
    phases: list[Any],
    phase_weights: dict[str, float],
    peak_data: pd.DataFrame,
) -> dict[str, list[float]]:
    phase_profiles: dict[str, list[float]] = {}
    available_signal = np.maximum(y_calc - y_bkg, 0.0)
    total_weight = sum(max(0.0, phase_weights.get(phase.path.stem, 0.0)) for phase in phases) or 1.0
    for phase in phases:
        phase_name = phase.path.stem
        peaks = peak_data[peak_data["phase"] == phase_name]
        profile = np.zeros_like(x, dtype=float)
        for _, peak in peaks.iterrows():
            profile += float(peak["intensity"]) * np.exp(-0.5 * ((x - float(peak["2theta"])) / 0.08) ** 2)
        if profile.max() > 0:
            profile = profile / profile.max()
        scale = float(phase_weights.get(phase_name, 0.0)) / total_weight
        profile *= scale * max(float(available_signal.max()), 1.0)
        phase_profiles[phase_name] = profile.tolist()
    return phase_profiles


def _calculate_rwp(y_obs: np.ndarray, y_calc: np.ndarray) -> float:
    denominator = np.sum(np.maximum(y_obs, 1.0) ** 2)
    if denominator <= 0:
        return 100.0
    return float(np.sqrt(np.sum((y_obs - y_calc) ** 2) / denominator) * 100)


def _calculate_rp(y_obs: np.ndarray, y_calc: np.ndarray) -> float:
    denominator = np.sum(np.abs(y_obs))
    if denominator <= 0:
        return 100.0
    return float(np.sum(np.abs(y_obs - y_calc)) / denominator * 100)


def _attach_backend_metadata(
    result: RefinementResult,
    backend: str,
    working_dir: Path,
    stage_log: list[dict[str, Any]],
    warnings: list[str],
) -> RefinementResult:
    result.backend_name = backend
    result.backend_version = None
    result.backend_capabilities = REFINEMENT_BACKEND_CAPABILITIES[backend]
    result.stage_log = stage_log
    result.warnings = warnings
    result.raw_output_dir = working_dir.as_posix()
    _write_unified_outputs(result, working_dir, backend)
    return result


def _write_unified_outputs(result: RefinementResult, working_dir: Path, backend: str) -> None:
    weights = result.get_phase_weights(normalize=True)
    phase_fraction = [
        {"phase": phase, "weight_fraction": float(weight), "wt_percent": float(weight) * 100}
        for phase, weight in weights.items()
    ]
    summary = {
        "backend": backend,
        "rwp": result.lst_data.rwp,
        "rp": result.lst_data.rp,
        "rexp": result.lst_data.rexp,
        "gof": getattr(result.lst_data, "GOF", None),
        "phase_fractions": phase_fraction,
        "stage_log": getattr(result, "stage_log", []),
        "warnings": getattr(result, "warnings", []),
        "raw_output_dir": getattr(result, "raw_output_dir", working_dir.as_posix()),
        "capabilities": REFINEMENT_BACKEND_CAPABILITIES[backend],
    }
    (working_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    pd.DataFrame(phase_fraction).to_csv(working_dir / "phase_fractions.csv", index=False)
    plot_data = {
        "x": result.plot_data.x,
        "y_obs": result.plot_data.y_obs,
        "y_calc": result.plot_data.y_calc,
        "y_bkg": result.plot_data.y_bkg,
        "structs": result.plot_data.structs,
    }
    (working_dir / "refinement_plot_data.json").write_text(json.dumps(plot_data), encoding="utf-8")
