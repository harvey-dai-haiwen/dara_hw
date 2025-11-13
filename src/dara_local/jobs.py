"""Jobflow jobs for DARA Local Server."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Union, cast

from dara.schema import PhaseSearchDocument
from dara.search import search_phases
from dara.search.data_model import SearchResult

if TYPE_CHECKING:
    from dara.xrd import XRDData

try:
    from jobflow import Maker, job
except ImportError:
    raise ImportError(
        "Please install jobflow to use the dara_local jobs module! (pip install 'dara[jobflow]')"
    )


@dataclass
class LocalPhaseSearchMaker(Maker):
    """Maker to create a job for performing local database phase search using BGMN.
    
    This is a simplified version of PhaseSearchMaker that works with pre-filtered
    database phases from prepare_phases_for_dara instead of phase prediction.
    
    Args:
        name: The name of the job. This is automatically created if not provided.
        max_num_results: Maximum number of results to return.
    """

    name: str = "local_phase_search"
    max_num_results: int | None = 10

    @job(output_schema=PhaseSearchDocument)
    def make(
        self,
        pattern_path: str | Path,
        database_cifs: list[Union[str, Path]],
        wavelength: str | float = "Cu",
        instrument_profile: str = "Aeris-fds-Pixcel1d-Medipix3",
        cleanup_dirs: list[str] | None = None,
    ):
        """Perform phase search with pre-filtered database CIFs.

        Args:
            pattern_path: Path to the XRD pattern file (will be loaded internally)
            database_cifs: List of CIF file paths from prepare_phases_for_dara
            wavelength: Wavelength for search (Cu/Co/Cr/Fe/Mo or numeric)
            instrument_profile: Instrument profile name
            cleanup_dirs: List of directories to cleanup after job completes

        Returns:
            PhaseSearchDocument containing search results
        """
        cleanup_dirs = cleanup_dirs or []

        directory = Path(os.getcwd()).resolve()
        
        # Pattern path is already provided, just convert to Path
        pattern_path = Path(pattern_path)

        # Validate and cast wavelength
        ALLOWED_WAVELENGTHS = {"Cu", "Co", "Cr", "Fe", "Mo"}
        if isinstance(wavelength, str):
            if wavelength not in ALLOWED_WAVELENGTHS:
                try:
                    wavelength = float(wavelength)
                except ValueError:
                    raise ValueError(f"Invalid wavelength: {wavelength}")
            else:
                wavelength = cast(Literal["Cu", "Co", "Cr", "Fe", "Mo"], wavelength)

        # Normalize CIF paths to Path objects
        cif_paths = [Path(p) for p in database_cifs]
        
        # Load XRD data from pattern file for PhaseSearchDocument
        from dara.xrd import XYFile, XRDMLFile, RawFile
        
        pattern_path_obj = Path(pattern_path)
        if pattern_path_obj.suffix in ['.xy', '.txt', '.xye']:
            xrd_data = XYFile.from_file(str(pattern_path_obj))
        elif pattern_path_obj.suffix == '.xrdml':
            xrd_data = XRDMLFile.from_file(str(pattern_path_obj))
        elif pattern_path_obj.suffix == '.raw':
            xrd_data = RawFile.from_file(str(pattern_path_obj))
        else:
            raise ValueError(f"Unsupported pattern file format: {pattern_path_obj.suffix}")

        try:
            # Run search_phases with database CIFs
            results = search_phases(
                pattern_path=str(pattern_path),
                phases=cif_paths,
                wavelength=wavelength,
                instrument_profile=instrument_profile,
            )
        finally:
            for dir_path in cleanup_dirs:
                shutil.rmtree(dir_path, ignore_errors=True)

        # Sort by RWP and limit results
        results = sorted(results, key=lambda x: x.refinement_result.lst_data.rwp)[
            : self.max_num_results
        ]

        # Parse results similar to PhaseSearchMaker
        from dara.cif import Cif

        parsed_results = [
            (
                [
                    [Cif.from_file(phase.path) for phase in phases]
                    for phases in result.phases
                ],
                result.refinement_result,
            )
            for result in results
        ]
        
        # Get grouped_phases with error handling for CIF files without formula in filename
        # (e.g., ICSD/COD files named as "123456.cif" instead of "Formula_123456.cif")
        grouped_phases = []
        for r in results:
            try:
                grouped_phases.append(r.grouped_phases)
            except (ValueError, AttributeError) as e:
                # If composition parsing fails (e.g., filename doesn't contain formula),
                # use empty list for this result
                grouped_phases.append([])

        # Convert Path to str for serialization
        for i in range(len(grouped_phases)):
            for j in range(len(grouped_phases[i])):
                for k in range(len(grouped_phases[i][j])):
                    grouped_phases[i][j][k] = (
                        grouped_phases[i][j][k][0],
                        [p.stem for p in grouped_phases[i][j][k][1]],
                    )

        foms = [[list(f) for f in r.foms] for r in results]
        lattice_strains = [[list(ls) for ls in r.lattice_strains] for r in results]
        missing_peaks = [r.missing_peaks for r in results]
        extra_peaks = [r.extra_peaks for r in results]

        all_rwp = [i[1].lst_data.rwp for i in parsed_results]
        best_rwp = min(all_rwp, default=None)

        return PhaseSearchDocument(
            task_label=self.name,
            results=parsed_results,
            foms=foms,
            lattice_strains=lattice_strains,
            missing_peaks=missing_peaks,
            extra_peaks=extra_peaks,
            final_result=None,  # No final refinement in local search
            best_rwp=best_rwp,
            xrd_data=xrd_data,
            input_cifs=None,  # CIFs come from database
            precursors=None,  # No precursors in local search
            phase_predictor=None,
            predict_kwargs=None,
            search_kwargs={
                "wavelength": wavelength,
                "instrument_profile": instrument_profile,
            },
            final_refinement_params=None,
            run_final_refinement=False,
            cifs_folder_name="database_cifs",
            grouped_phases=grouped_phases,
        )
