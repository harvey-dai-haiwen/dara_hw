"""
Extension to api_router.py for local database support.
This file adds a new /api/search endpoint that uses prepare_phases_for_dara.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from pathlib import Path
from traceback import print_exc
from typing import Annotated, Literal, Union, cast

from fastapi import File, Form, HTTPException, UploadFile
from pymatgen.core import Composition

from dara.xrd import RawFile, XRDMLFile, XYFile
from dara_local.server.api_router import router
from dara_local.server.worker import add_job_to_queue
from dara_local.jobs import LocalPhaseSearchMaker

# Import the database adapter
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_PATH = REPO_ROOT / "scripts"
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

from dara_adapter import prepare_phases_for_dara


@router.get("/debug/cifs")
async def debug_get_cifs(
    database: Literal["COD", "ICSD", "MP"],
    required_elements: str,
    exclude_elements: str = "",
    max_phases: int = 500,
):
    """
    Debug endpoint to see which CIF files would be used for a search.
    
    Example: /debug/cifs?database=ICSD&required_elements=Y,Cl&max_phases=100
    """
    repo_root = REPO_ROOT
    
    # Parse elements
    required_elements_list = [e.strip() for e in required_elements.split(",") if e.strip()]
    exclude_elements_list = [e.strip() for e in exclude_elements.split(",") if e.strip()] if exclude_elements else []
    
    # Get index path
    if database == "ICSD":
        index_path = repo_root / "indexes" / "icsd_index_filled.parquet"
    elif database == "COD":
        index_path = repo_root / "indexes" / "cod_index_filled.parquet"
    elif database == "MP":
        index_path = repo_root / "indexes" / "mp_index.parquet"
    else:
        raise HTTPException(status_code=400, detail=f"Invalid database: {database}")
    
    if not index_path.exists():
        raise HTTPException(status_code=404, detail=f"Index not found: {index_path}")
    
    # Get CIFs
    database_cifs = prepare_phases_for_dara(
        index_path=index_path,
        required_elements=required_elements_list,
        exclude_elements=exclude_elements_list,
        max_phases=max_phases,
    )
    
    # Format response
    cif_info = []
    for cif_path in database_cifs:
        path_obj = Path(cif_path)
        cif_info.append({
            "filename": path_obj.name,
            "full_path": str(cif_path),
            "exists": path_obj.exists(),
        })
    
    return {
        "database": database,
        "required_elements": required_elements_list,
        "exclude_elements": exclude_elements_list,
        "max_phases": max_phases,
        "total_cifs_found": len(database_cifs),
        "cifs": cif_info,
    }


ALLOWED_WAVELENGTHS: set[str] = {"Cu", "Co", "Cr", "Fe", "Mo"}


@router.post("/search")
async def search_with_local_db(
    pattern_file: Annotated[UploadFile, File()],
    required_elements: Annotated[str, Form()],  # JSON list as string
    user: Annotated[str, Form()],
    database: Annotated[str, Form()] = "COD",  # COD, ICSD, MP, NONE
    exclude_elements: Annotated[str, Form()] = "[]",  # JSON list as string
    instrument_profile: Annotated[str, Form()] = "Aeris-fds-Pixcel1d-Medipix3",
    wavelength: Annotated[str, Form()] = "Cu",
    mp_experimental_only: Annotated[bool, Form()] = False,
    mp_max_e_above_hull: Annotated[float, Form()] = 0.1,
    max_phases: Annotated[int, Form()] = 500,
    additional_phases: Annotated[list[UploadFile], File()] = None,
):
    """
    Search phases using local COD/ICSD/MP databases (async job submission).
    
    This endpoint mirrors the streamlined notebook Part 1-2 behavior:
    - Accepts required_elements (list of element symbols)
    - Selects database: COD, ICSD, MP, or NONE
    - Filters phases using subset-based chemical system logic
    - Supports custom CIF uploads
    - Submits job to queue and returns job ID for polling
    
    After submission, poll /api/task/{wf_id} for status and results.
    """
    try:
        # Parse elements
        import json
        try:
            required_elements_list = json.loads(required_elements)
            exclude_elements_list = json.loads(exclude_elements)
            if not isinstance(required_elements_list, list):
                raise ValueError("required_elements must be a list")
            if not isinstance(exclude_elements_list, list):
                raise ValueError("exclude_elements must be a list")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid element format: {e}")

        # Validate elements
        try:
            for el in required_elements_list + exclude_elements_list:
                Composition(el)  # Validate each element
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid element symbols")

        # Parse wavelength
        try:
            wavelength_val: Union[float, str] = float(wavelength)
        except ValueError:
            wavelength_clean = wavelength.strip()
            if wavelength_clean not in ALLOWED_WAVELENGTHS:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Invalid wavelength. Provide a numeric value in Å or one of "
                        f"{sorted(ALLOWED_WAVELENGTHS)}"
                    ),
                )
            wavelength_val = wavelength_clean

        # Create persistent upload directory for this job
        uploads_base = Path.home() / ".dara-local-server" / "uploads"
        uploads_base.mkdir(parents=True, exist_ok=True)
        job_uuid = uuid.uuid4().hex
        job_upload_dir = uploads_base / job_uuid
        job_upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save pattern file to persistent location
        name = pattern_file.filename or "uploaded_pattern.xy"
        pattern_save_path = job_upload_dir / f"pattern_{name}"
        
        with open(pattern_save_path, "wb") as dest:
            shutil.copyfileobj(pattern_file.file, dest)
        
        # Load pattern file into XRDData from persistent location
        if name.endswith(".xy") or name.endswith(".txt") or name.endswith(".xye"):
            pattern = XYFile.from_file(str(pattern_save_path))
        elif name.endswith(".xrdml"):
            pattern = XRDMLFile.from_file(str(pattern_save_path))
        elif name.endswith(".raw"):
            pattern = RawFile.from_file(str(pattern_save_path))
        else:
            raise HTTPException(status_code=400, detail="Invalid file format")

        # Get database CIFs using prepare_phases_for_dara
        repo_root = REPO_ROOT
        if database == "COD":
            index_path = repo_root / "indexes" / "cod_index_filled.parquet"
            if not index_path.exists():
                raise HTTPException(status_code=400, detail=f"COD index not found at {index_path}")
            database_cifs = prepare_phases_for_dara(
                index_path=index_path,
                required_elements=required_elements_list,
                exclude_elements=exclude_elements_list,
                max_phases=max_phases,
            )
        elif database == "ICSD":
            index_path = repo_root / "indexes" / "icsd_index_filled.parquet"
            if not index_path.exists():
                raise HTTPException(status_code=400, detail=f"ICSD index not found at {index_path}")
            
            print(f"\n{'='*70}")
            print(f"📊 ICSD Database Query Debug Info")
            print(f"{'='*70}")
            print(f"Required elements: {required_elements_list}")
            print(f"Exclude elements: {exclude_elements_list}")
            print(f"Max phases: {max_phases}")
            
            database_cifs = prepare_phases_for_dara(
                index_path=index_path,
                required_elements=required_elements_list,
                exclude_elements=exclude_elements_list,
                max_phases=max_phases,
            )
            
            print(f"\n✅ Found {len(database_cifs)} CIF files from ICSD")
            print(f"\nFirst 10 CIF files:")
            for i, cif in enumerate(database_cifs[:10], 1):
                cif_name = Path(cif).name
                print(f"  {i}. {cif_name} -> {cif}")
            if len(database_cifs) > 10:
                print(f"  ... and {len(database_cifs) - 10} more")
            print(f"{'='*70}\n")
        elif database == "MP":
            index_path = repo_root / "indexes" / "mp_index.parquet"
            if not index_path.exists():
                raise HTTPException(status_code=400, detail=f"MP index not found at {index_path}")
            database_cifs = prepare_phases_for_dara(
                index_path=index_path,
                required_elements=required_elements_list,
                exclude_elements=exclude_elements_list,
                experimental_only=mp_experimental_only,
                include_theoretical=not mp_experimental_only,
                max_e_above_hull=mp_max_e_above_hull,
                max_phases=max_phases,
            )
        elif database == "NONE":
            database_cifs = []
        else:
            raise HTTPException(status_code=400, detail=f"Invalid database: {database}")

        database_cifs = [str(Path(p)) for p in database_cifs]
        cleanup_dirs: list[str] = [str(job_upload_dir)]

        # Handle custom CIF uploads
        if additional_phases:
            additional_cifs_dir_path = job_upload_dir / "custom_cifs"
            additional_cifs_dir_path.mkdir(parents=True, exist_ok=True)

            for phase in additional_phases:
                phase_name = (phase.filename or "custom.cif").split("/")[-1].split("\\")[-1]
                dest_path = additional_cifs_dir_path / phase_name
                with open(dest_path, "wb") as dest:
                    phase.file.seek(0)
                    shutil.copyfileobj(phase.file, dest)
                database_cifs.append(str(dest_path))

        if len(database_cifs) == 0:
            raise HTTPException(status_code=400, detail="No CIF files available for search")

        # Create job using LocalPhaseSearchMaker
        job = LocalPhaseSearchMaker(name=name, max_num_results=10).make(
            pattern_path=str(pattern_save_path),  # Pass file path, not XRDData object
            database_cifs=database_cifs,
            wavelength=wavelength_val,
            instrument_profile=instrument_profile,
            cleanup_dirs=cleanup_dirs,
        )

        # Submit to queue
        job_index = add_job_to_queue(job, user=user)
        
        return {
            "message": "submitted",
            "wf_id": job_index,
            "database": database,
            "num_phases_queued": len(database_cifs),
            "job_upload_dir": str(job_upload_dir),
            "note": "Job submitted to queue. Poll /api/task/{wf_id} for status and results."
        }

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        print_exc()
        raise HTTPException(status_code=400, detail=str(e))
