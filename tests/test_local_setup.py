from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path

from dara.structure_db import MPDatabase


def test_mp_json_index_loader(tmp_path: Path):
    index_path = tmp_path / "mp_index.jsonl.gz"
    rows = [
        {
            "raw_db_id": "mp-1",
            "formula": "Fe2O3",
            "elements": ["Fe", "O"],
            "spacegroup": 167,
            "energy_above_hull": 0.0,
        },
        {
            "raw_db_id": "mp-2",
            "formula": "BiFeO3",
            "elements": ["Bi", "Fe", "O"],
            "spacegroup": 161,
            "energy_above_hull": 0.01,
        },
    ]
    with gzip.open(index_path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")

    loaded = MPDatabase._load_json_index(index_path)

    assert loaded["Fe-O"] == [("Fe2O3", "mp-1", 167, 0.0)]
    assert loaded["Bi-Fe-O"] == [("BiFeO3", "mp-2", 161, 0.01)]


def test_setup_local_dara_layout(tmp_path: Path):
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "setup_local_dara.py"
    spec = importlib.util.spec_from_file_location("setup_local_dara", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)

    module.ensure_layout(tmp_path)

    for relative in ("cod_cifs", "cod_cifs/cif", "icsd_cifs", "icsd_cifs/cif", "mp_cifs", "indexes", "downloads"):
        assert (tmp_path / relative).is_dir()
        assert (tmp_path / relative / ".gitkeep").exists()


def test_setup_local_dara_finds_cloned_mp_pickle(tmp_path: Path):
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "setup_local_dara.py"
    spec = importlib.util.spec_from_file_location("setup_local_dara", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)

    mp_pickle = tmp_path / "indexes" / module.MPINICSD_PICKLE_NAME
    mp_pickle.parent.mkdir(parents=True)
    mp_pickle.write_bytes(b"pickle")

    assert module.resolve_mp_pickle_source(None, tmp_path) == mp_pickle


def test_check_database_sources_lfs_pointer(tmp_path: Path, monkeypatch):
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check_database_sources.py"
    monkeypatch.syspath_prepend(str(script_path.parent))
    spec = importlib.util.spec_from_file_location("check_database_sources", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)

    pointer = tmp_path / "df_MPinICSD_20250211_withstructure.pkl"
    pointer.write_text(
        "\n".join(
            [
                "version https://git-lfs.github.com/spec/v1",
                "oid sha256:d8e08bf17e412564d8af29d1d2b316a6f369eed8d07d51cc149cb8c42ba2f51a",
                "size 716995773",
                "",
            ]
        ),
        encoding="utf-8",
    )

    report = module.inspect_lfs_pointer(pointer)

    assert report["ok"] is True
    assert report["size"] == 716995773
