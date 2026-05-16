from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import dara.refinement_backends as refinement_backends
from dara.result import PhaseResult
from dara.refine import RefinementPhase, do_refinement_no_saving
from dara.refinement_backends import (
    REFINEMENT_BACKEND_CAPABILITIES,
    BackendRunContext,
    normalize_backend,
    parse_fullprof_prf,
    parse_fullprof_sum,
)


TEST_DATA = Path(__file__).parent / "test_data"


def test_backend_registry_resolves_known_backends():
    assert normalize_backend("bgmn") == "bgmn"
    assert normalize_backend("gsas") == "gsas"
    assert normalize_backend("fullprof") == "fullprof"
    assert REFINEMENT_BACKEND_CAPABILITIES["bgmn"]["supports_multiphase"]
    assert not REFINEMENT_BACKEND_CAPABILITIES["fullprof"]["supports_multiphase"]


def test_unknown_backend_rejected():
    with pytest.raises(ValueError):
        do_refinement_no_saving(
            TEST_DATA / "BiFeO3.xy",
            [TEST_DATA / "BiFeO3.cif"],
            backend="not-a-backend",
        )


def test_fullprof_sum_and_prf_parsers(tmp_path):
    sum_path = tmp_path / "candidate.sum"
    sum_path.write_text(
        """
 Conventional Rietveld Rp,Rwp,Re and Chi2:   12.0      8.50      4.25      4.00
 => Phase:  1     candidate.cif
 => Bragg R-factor:   6.2       Vol:  100.0( 0.1)  Fract(%):  75.50(1.00)
 Cell parameters :  5.1  5.2  5.3  90.0  91.0  120.0
""",
        encoding="utf-8",
    )
    metrics, fractions, cells = parse_fullprof_sum(sum_path)
    assert metrics["Rwp"] == pytest.approx(8.5)
    assert metrics["GOF"] == pytest.approx(2.0)
    assert fractions["candidate"] == pytest.approx(75.5)
    assert cells["candidate"] == pytest.approx((5.1, 5.2, 5.3, 90.0, 91.0, 120.0))

    prf_path = tmp_path / "candidate.prf"
    prf_path.write_text(
        """
  2Theta Yobs Ycal Yobs-Ycal Backg
    5.0  100.0  95.0  5.0  10.0
    5.1  120.0  118.0  2.0  11.0
""",
        encoding="utf-8",
    )
    arrays = parse_fullprof_prf(prf_path)
    assert arrays["x"] == [5.0, 5.1]
    assert arrays["y_bkg"] == [10.0, 11.0]


def test_backend_result_schema_exports_phase_fractions(tmp_path, monkeypatch):
    phase = RefinementPhase(path=TEST_DATA / "BiFeO3.cif")
    monkeypatch.setattr(
        refinement_backends,
        "_simulate_backend_peaks",
        lambda phases, wavelength: pd.DataFrame(
            [
                {
                    "2theta": 32.0,
                    "intensity": 100.0,
                    "b1": 0.0,
                    "b2": 0.0,
                    "h": 1,
                    "k": 0,
                    "l": 0,
                    "phase": phases[0].path.stem,
                    "phase_idx": 0,
                }
            ]
        ),
    )
    monkeypatch.setattr(
        refinement_backends,
        "_make_phase_result",
        lambda cif_path, weight_fraction, refined_cell=None: PhaseResult(
            SpacegroupNo=1,
            HermannMauguin="P1",
            XrayDensity=1.0,
            Rphase=0.0,
            UNIT="NM",
            GEWICHT=float(weight_fraction),
            A=1.0,
            B=1.0,
            C=1.0,
            ALPHA=90.0,
            BETA=90.0,
            GAMMA=90.0,
            atom_positions_string="1 0.0000 0.0000 0.0000 E=(FE(1.0000))",
        ),
    )
    x = np.linspace(10, 80, 100)
    y_obs = np.exp(-0.5 * ((x - 32) / 0.5) ** 2) * 1000 + 50
    y_calc = y_obs * 0.95
    context = BackendRunContext(
        pattern_path=TEST_DATA / "BiFeO3.xy",
        phases=[phase],
        wavelength="Cu",
        instrument_profile="Aeris-fds-Pixcel1d-Medipix3",
        working_dir=tmp_path,
    )
    result = refinement_backends._build_backend_result(
        context=context,
        backend="gsas",
        phases=[phase],
        metrics={"Rwp": 7.0, "Rp": 5.0, "Rexp": 2.0, "GOF": 3.5},
        phase_weights={phase.path.stem: 42.0},
        plot_arrays={
            "x": x.tolist(),
            "y_obs": y_obs.tolist(),
            "y_calc": y_calc.tolist(),
            "y_bkg": [50.0] * len(x),
        },
        stage_log=[{"stage": "unit-test", "status": "ok"}],
        warnings=[],
        elapsed_seconds=0.1,
    )
    weights = result.get_phase_weights(normalize=True)
    assert sum(weights.values()) == pytest.approx(1.0)
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "phase_fractions.csv").exists()
    assert (tmp_path / "refinement_plot_data.json").exists()
