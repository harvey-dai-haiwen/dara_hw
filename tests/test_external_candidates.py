from pathlib import Path

from pymatgen.core import Lattice, Structure
from pymatgen.io.cif import CifWriter

from dara.external_candidates import deduplicate_external_cifs, prepare_external_cifs_from_csv


def write_cif(path: Path, structure: Structure) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    CifWriter(structure).write_file(path)


def nacl_structure(a: float = 5.64) -> Structure:
    return Structure(
        Lattice.cubic(a),
        ["Na", "Cl"],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
    )


def test_prepare_external_cifs_from_csv_detects_and_symmetrizes_cif_column(tmp_path):
    source = tmp_path / "source.cif"
    write_cif(source, nacl_structure())
    csv_path = tmp_path / "external.csv"
    escaped_cif = source.read_text(encoding="utf-8").replace('"', '""')
    csv_path.write_text(
        "immutable_id,chemsys,cif_optimized_test\n"
        f'row_a,Cl-Na,"{escaped_cif}"\n',
        encoding="utf-8",
    )

    result = prepare_external_cifs_from_csv(csv_path, tmp_path / "prepared")

    assert result.manifest["generated_count"] == 1
    assert result.manifest["failure_count"] == 0
    assert result.manifest["cif_column"] == "cif_optimized_test"
    assert result.cif_paths[0].exists()


def test_deduplicate_external_cifs_prefers_primary_structures(tmp_path):
    primary = tmp_path / "primary" / "icsd_1.cif"
    duplicate_external = tmp_path / "external" / "wf_duplicate.cif"
    new_external = tmp_path / "external" / "wf_new.cif"

    write_cif(primary, nacl_structure())
    write_cif(duplicate_external, nacl_structure())
    write_cif(
        new_external,
        Structure(
            Lattice.cubic(5.8),
            ["K", "Cl"],
            [[0, 0, 0], [0.5, 0.5, 0.5]],
        ),
    )

    result = deduplicate_external_cifs([primary], [duplicate_external, new_external])

    assert result.kept_external_paths == [new_external]
    assert len(result.duplicates) == 1
    assert result.duplicates[0].external_path == duplicate_external
    assert result.duplicates[0].matched_path == primary
