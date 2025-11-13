from __future__ import annotations

import os
import shutil
import tempfile
from ast import literal_eval
from pathlib import Path
from traceback import print_exc
from typing import Annotated, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from monty.serialization import MontyDecoder
from pymatgen.core import Composition

from dara.cif import Cif
from dara.jobs import PhaseSearchMaker
from dara.plot import visualize
from dara_local.server.utils import convert_to_local_tz, get_result_store, get_worker_store
from dara_local.server.worker import (
    add_job_to_queue,
)
from dara.structure_db import CODDatabase
from dara.utils import (
    get_compositional_clusters,
    get_head_of_compositional_cluster,
)
from dara.xrd import RawFile, XRDMLFile, XYFile
from dara import search_phases

# Import the database adapter
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'scripts'))
from dara_adapter import prepare_phases_for_dara

router = APIRouter(prefix="/api")


@router.post("/submit")
async def submit(
    pattern_file: Annotated[UploadFile, File()],
    precursor_formulas: Annotated[str, Form()],
    user: Annotated[str, Form()],
    instrument_profile: Annotated[str, Form()] = "Aeris-fds-Pixcel1d-Medipix3",
    wavelength: Annotated[str, Form()] = "Cu",
    temperature: Annotated[int, Form()] = -1,
    use_rxn_predictor: Annotated[bool, Form()] = True,
    additional_phases: Annotated[list[UploadFile], File()] = None,
):
    try:
        name = pattern_file.filename
        with tempfile.NamedTemporaryFile() as temp:
            temp.write(pattern_file.file.read())
            temp.seek(0)
            if name.endswith(".xy") or name.endswith(".txt") or name.endswith(".xye"):  # noqa: PIE810
                pattern = XYFile.from_file(temp.name)
            elif name.endswith(".xrdml"):
                pattern = XRDMLFile.from_file(temp.name)
            elif name.endswith(".raw"):
                pattern = RawFile.from_file(temp.name)
            else:
                print(pattern_file.filename)
                raise HTTPException(status_code=400, detail="Invalid file format")

        precursor_formulas = literal_eval(precursor_formulas)

        if additional_phases:
            additional_cifs = []
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir = Path(temp_dir)
                for phase in additional_phases:
                    with open(temp_dir / phase.filename, "wb") as f:
                        shutil.copyfileobj(phase.file, f)
                        additional_cifs.append(Cif.from_file(temp_dir / phase.filename))
        else:
            additional_cifs = None

        try:
            [Composition(p) for p in precursor_formulas]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid precursor formulas")

        try:
            wavelength = float(wavelength)
        except ValueError:
            pass

        if use_rxn_predictor:
            try:
                import mp_api  # noqa: F401
            except ImportError:
                raise HTTPException(
                    status_code=400,
                    detail="Reaction predictor is not available. Please install mp_api.",
                )
            if not os.environ.get("MP_API_KEY"):
                raise HTTPException(
                    status_code=400,
                    detail="MP_API_KEY is not set. You need to `export MP_API_KEY=your_key` in "
                    "your terminal before launching the server to use reaction predictor.",
                )
            if temperature < -273:
                raise HTTPException(
                    status_code=400,
                    detail="Temperature should be >= -273 when using reaction predictor",
                )
            job = PhaseSearchMaker(name=name, verbose=False, max_num_results=5).make(
                pattern,
                precursors=precursor_formulas,
                predict_kwargs={"temp": temperature + 273},
                cif_dbs=[CODDatabase()],
                additional_cifs=additional_cifs,
                additional_cif_params={"lattice_range": 0.05},
                search_kwargs={
                    "instrument_profile": instrument_profile,
                    "wavelength": wavelength,
                },
            )
        else:
            if temperature >= -273:
                raise HTTPException(
                    status_code=400,
                    detail="Temperature is not required when not using reaction predictor",
                )
            job = PhaseSearchMaker(
                name=name, verbose=False, phase_predictor=None, max_num_results=5
            ).make(
                pattern,
                precursors=precursor_formulas,
                cif_dbs=[CODDatabase()],
                additional_cifs=additional_cifs,
                additional_cif_params={"lattice_range": 0.05},
                search_kwargs={
                    "instrument_profile": instrument_profile,
                    "wavelength": wavelength,
                },
            )
        job_index = add_job_to_queue(job, user=user)
        return {"message": "submitted", "wf_id": job_index}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/task/{task_id}")
async def result(task_id: int):
    # get the task state
    with get_worker_store() as worker_store:
        job = worker_store.query_one({"index": task_id})

    if job is None:
        raise HTTPException(status_code=404, detail="Task not found")

    job_name = job["job"]["name"]

    if job["status"] == "READY":
        return {
            "task_label": job_name,
            "status": job["status"],
            "submitted_on": convert_to_local_tz(job["submitted_time"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }

    if job["status"] == "RUNNING":
        return {
            "task_label": job_name,
            "status": job["status"],
            "submitted_on": convert_to_local_tz(job["submitted_time"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "start_time": convert_to_local_tz(job["start_time"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }

    if job["status"] == "FIZZLED":
        return {
            "task_label": job_name,
            "status": job["status"],  # FIZZLED
            "submitted_on": convert_to_local_tz(job["submitted_time"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "start_time": convert_to_local_tz(job["start_time"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "end_time": convert_to_local_tz(job["end_time"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "error_tb": job["error"],
        }

    with get_result_store() as result_store:
        d = result_store.query_one({"uuid": job["uuid"]})
    if d is None:
        raise HTTPException(status_code=404, detail="Task result not found")
    d = MontyDecoder().process_decoded(d["output"])

    # Build a global filename -> formula mapping from all CIF objects
    global_filename_to_formula = {}
    for result in d.results:
        for phase_cifs in result[0]:  # result[0] is list of phase lists
            for cif in phase_cifs:
                if cif.filename not in global_filename_to_formula:
                    try:
                        structure = cif.to_structure()
                        formula = structure.composition.reduced_formula
                        # Format: "Formula (ID)" e.g. "YMoO₃ (254377)"
                        global_filename_to_formula[cif.filename] = f"{formula} ({cif.filename})"
                    except Exception:
                        # If can't parse structure, just use filename
                        global_filename_to_formula[cif.filename] = cif.filename

    all_results = []

    for result in d.results:
        # Get grouped_phases for this result if available
        result_grouped_phases = (
            d.grouped_phases[len(all_results)] if d.grouped_phases and len(all_results) < len(d.grouped_phases) else None
        )
        
        # Create phases with enriched names using global mapping
        phases = [[global_filename_to_formula.get(cif.filename, cif.filename) for cif in cifs] for cifs in result[0]]
        # Also keep original filenames for backward compatibility with clustering
        phases_raw = [[cif.filename for cif in cifs] for cifs in result[0]]

        # If grouped_phases not available or empty, try to compute them for backward compatibility
        if not result_grouped_phases:
            grouped_phases = []
            for i, phases_ in enumerate(phases):
                try:
                    # Use raw filenames for compositional clustering
                    grouped_phase = get_compositional_clusters(phases_raw[i])
                    grouped_phase_with_head = [
                        (get_head_of_compositional_cluster(cluster), cluster)
                        for cluster in grouped_phase
                    ]
                    grouped_phases.append(grouped_phase_with_head)
                except (ValueError, AttributeError):
                    # Handle COD-style filenames: use enriched names
                    grouped_phases.append([(name, [name]) for name in phases_])
        else:
            grouped_phases = result_grouped_phases

        # convert composition into formula (skip if grouped_phases contains strings instead of Composition objects)
        for i in range(len(grouped_phases)):
            for j in range(len(grouped_phases[i])):
                head_comp = grouped_phases[i][j][0]
                cluster = grouped_phases[i][j][1]
                
                # Check if head_comp is a Composition object with reduced_composition method
                if hasattr(head_comp, 'reduced_composition'):
                    formula = (
                        head_comp.reduced_composition.to_html_string()
                        .replace("<sub>1</sub>", "")
                    )
                    # Map cluster filenames to enriched names
                    enriched_cluster = [global_filename_to_formula.get(fn, fn) for fn in cluster]
                    grouped_phases[i][j] = (formula, enriched_cluster)
                # Otherwise keep as-is (already enriched for COD numeric filenames)

        # Enrich highlighted_phases with formula information
        highlighted_phases_enriched = [
            global_filename_to_formula.get(fn, fn) for fn in result[1].lst_data.phases_results
        ]
        
        all_results.append(
            {
                "rwp": result[1].lst_data.rwp,
                "phases": phases,
                "highlighted_phases": highlighted_phases_enriched,
                "grouped_phases": grouped_phases,
            }
        )

    # Check if we have results to return
    if not all_results:
        raise HTTPException(status_code=404, detail="No phases identified in the pattern")
    
    # Build final_result (use best result or first result if final_result is None)
    if d.final_result is not None:
        final_result_data = {
            "rwp": d.final_result.lst_data.rwp,
            "phases": [global_filename_to_formula.get(fn, fn) for fn in d.final_result.lst_data.phases_results],
        }
    else:
        # Use the best result from all_results (lowest RWP)
        best_result = min(d.results, key=lambda r: r[1].lst_data.rwp)
        final_result_data = {
            "rwp": best_result[1].lst_data.rwp,
            "phases": [global_filename_to_formula.get(fn, fn) for fn in best_result[1].lst_data.phases_results],
        }

    start_time = convert_to_local_tz(job["start_time"])
    end_time = convert_to_local_tz(job["end_time"])
    runtime = (end_time - start_time).total_seconds()
    
    return {
        "status": job["status"],
        "task_label": job["job"]["name"],
        "best_rwp": d.best_rwp,
        "final_result": final_result_data,
        "all_results": all_results,
        "precursors": d.precursors,
        "temperature": (
            None
            if not d.predict_kwargs or d.predict_kwargs.get("temp", None) is None
            else d.predict_kwargs["temp"] - 273
        ),
        "use_rxn_predictor": d.phase_predictor is not None,
        "submitted_on": convert_to_local_tz(job["submitted_time"]).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
        "runtime": runtime,
        "additional_search_options": d.search_kwargs,
    }


@router.get("/task/{task_id}/plot")
async def plot(task_id: int, idx: int = Query(None)):
    with get_worker_store() as worker_store:
        uuid = worker_store.query_one({"index": task_id}, ["uuid"])["uuid"]
    with get_result_store() as result_store:
        d = result_store.query_one({"uuid": uuid})
    if d is None:
        raise HTTPException(status_code=404, detail="Task not found")
    d = MontyDecoder().process_decoded(d["output"])
    if idx is None:
        return visualize(result=d.final_result).to_json()
    if 0 <= idx < len(d.results):
        result = d.results[idx][1]
        missing_peaks = d.missing_peaks[idx] if d.missing_peaks else None
        extra_peaks = d.extra_peaks[idx] if d.extra_peaks else None
        return visualize(
            result=result, missing_peaks=missing_peaks, extra_peaks=extra_peaks
        ).to_json()
    raise HTTPException(status_code=404, detail="Index out of range")


@router.get("/tasks")
async def get_all_tasks(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    user: Optional[str] = None,
):
    # Calculate the skip value based on the page and limit
    skip = (page - 1) * limit

    query_dict = {}
    if user is not None:
        query_dict["user"] = user
    if user == "unknown":
        query_dict["user"] = None
    with get_worker_store() as worker_store:
        tasks = worker_store.query(
            criteria=query_dict, sort={"submitted_time": -1}, skip=skip, limit=limit
        )

    tasks_result = []

    for task in tasks:
        index = task["index"]
        state = task["status"]
        tasks_result.append(
            {
                "fw_id": index,
                "name": task["job"]["name"],
                "state": state,
                "created_on": convert_to_local_tz(task["submitted_time"]).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "user": task.get("user", "unknown"),
            }
        )

    with get_worker_store() as worker_store:
        total_tasks = worker_store.count(query_dict)

    # Return the tasks data
    return {
        "tasks": tasks_result,
        "total_tasks": total_tasks,
        "page": page,
        "total_page": (total_tasks + limit - 1) // limit,
    }
