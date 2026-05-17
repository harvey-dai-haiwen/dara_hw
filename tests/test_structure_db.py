"""Tests for structure_db.py."""

import os
from pathlib import Path

import pytest
from pymatgen.core import Composition

from dara.structure_db import (
    CODDatabase,
    ICSDDatabase,
    MPDatabase,
    StructureDatabase,
    get_structure_database,
    get_structure_databases,
)
from dara.utils import get_composition_from_filename


REPO_ROOT = Path(__file__).resolve().parents[1]
STRUCTURE_INDEX_ROOT = Path(
    os.environ.get(
        "DARA_STRUCTURE_INDEX_ROOT",
        r"D:\Haiwen\Databases\Structure_index",
    )
)


class DummyStructureDatabase(StructureDatabase):
    def __init__(self, path_to_cifs: Path, db_name: str):
        super().__init__(path_to_cifs)
        self._db_name = db_name

    def get_file_path(self, cif_id: str | int):
        return self.path / f"{cif_id}.cif"

    def download_structures(self, ids=None, save=False, default_folder=None):
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self._db_name

    @property
    def default_folder_path(self) -> Path:
        return Path(self._path_to_cifs)


@pytest.fixture(scope="module")
def icsd_db():
    path = STRUCTURE_INDEX_ROOT / "icsd_cifs"
    if not path.exists():
        path = REPO_ROOT / "icsd_cifs"
    return ICSDDatabase(path)


@pytest.fixture(scope="module")
def cod_db():
    path = STRUCTURE_INDEX_ROOT / "cod_cifs"
    if not path.exists():
        path = REPO_ROOT / "cod_cifs"
    return CODDatabase(path)


@pytest.fixture(scope="module")
def mp_db():
    path = REPO_ROOT / "mp_test_cifs"
    if not path.exists():
        path = STRUCTURE_INDEX_ROOT / "mp_cifs"
    return MPDatabase(path)


def test_icsd_database(icsd_db):
    """Test the ICSDDatabase class."""
    cif_paths = icsd_db.get_cifs_by_chemsys("Fe-O", copy_files=False)
    assert len(cif_paths) > 0


def test_cod_database(cod_db):
    cif_paths = cod_db.get_cifs_by_chemsys("Fe-O", copy_files=False)
    assert len(cif_paths) > 0


def test_mp_database(mp_db):
    cif_paths = mp_db.get_cifs_by_chemsys("Fe-O", copy_files=False)
    assert len(cif_paths) > 0


def test_get_structure_database_returns_expected_type():
    assert isinstance(get_structure_database("cod"), CODDatabase)
    assert isinstance(get_structure_database("ICSD"), ICSDDatabase)
    assert isinstance(get_structure_database("mp"), MPDatabase)


def test_get_structure_databases_supports_csv_and_all():
    csv_names = [type(db).__name__ for db in get_structure_databases("COD, mp")]
    all_names = [type(db).__name__ for db in get_structure_databases("ALL")]

    assert csv_names == ["CODDatabase", "MPDatabase"]
    assert all_names == ["CODDatabase", "ICSDDatabase", "MPDatabase"]


def test_get_structure_database_rejects_unknown_name():
    with pytest.raises(ValueError, match="Unsupported database"):
        get_structure_database("unknown")


def test_mp_database_file_path_matches_repo_layout(mp_db):
    assert mp_db.get_file_path("mp-9").as_posix().endswith("0/00/mp-9.cif")
    assert mp_db.get_file_path("mp-90").as_posix().endswith("0/00/mp-90.cif")
    assert mp_db.get_file_path("mp-1026684").as_posix().endswith("1/10/mp-1026684.cif")
    assert mp_db.get_file_path("mvc-11882").as_posix().endswith("m/mv/mvc-11882.cif")


def test_icsd_database_file_path_matches_repo_layout(icsd_db):
    assert icsd_db.get_file_path("38768").as_posix().endswith("0/03/87/38768.cif")


@pytest.mark.parametrize(
    ("db_name", "db_code", "spacegroup", "expected_name"),
    [
        ("cod", "1000001", "P2_1/c", "cod_1000001.cif"),
        ("icsd", "123456", "C2/m", "icsd_123456.cif"),
        ("mp", "mp-1026684", "I4/mmm", "mp-1026684.cif"),
        ("mp", "mvc-11882", "R-3m", "mp_mvc-11882.cif"),
    ],
)
def test_generate_file_map_uses_database_ids_for_copied_names(
    tmp_path, db_name, db_code, spacegroup, expected_name
):
    source_path = tmp_path / f"{db_code}.cif"
    source_path.write_text("data_test")
    db = DummyStructureDatabase(tmp_path, db_name)

    file_map = db._generate_file_map(
        [("Fe2O3", db_code, spacegroup, 0.0)],
        e_hull_filter=0.1,
        exclude_gases=False,
    )

    assert file_map == {str(source_path): expected_name}


def test_get_composition_from_filename_supports_id_based_cif_names(tmp_path):
    source_cif = REPO_ROOT / "tests" / "test_data" / "BiFeO3.cif"
    copied_cif = tmp_path / "cod_123456.cif"
    copied_cif.write_text(source_cif.read_text())

    composition = get_composition_from_filename(copied_cif)

    assert composition == Composition("BiFeO3")
