from pathlib import Path

import pytest

from dara.candidate_filter import (
    CandidateElementFilter,
    cif_elements,
    collect_database_cifs,
    filter_cif_paths,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_DATA = REPO_ROOT / "tests" / "test_data"


class RecordingDatabase:
    def __init__(self, source_paths):
        self.source_paths = [Path(path) for path in source_paths]
        self.queries = []

    def get_cifs_by_chemsys(
        self,
        chemsys,
        e_hull_filter=0.1,
        copy_files=True,
        dest_dir="dara_cifs",
        exclude_gases=True,
    ):
        self.queries.append(
            {
                "chemsys": set(chemsys),
                "e_hull_filter": e_hull_filter,
                "copy_files": copy_files,
                "exclude_gases": exclude_gases,
            }
        )
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        for source_path in self.source_paths:
            (dest / source_path.name).write_text(source_path.read_text())


def test_candidate_filter_uses_plain_elements_for_charged_cifs():
    assert cif_elements(TEST_DATA / "BiFeO3.cif") == {"Bi", "Fe", "O"}


def test_candidate_filter_applies_must_any_possible_and_excludes_other_elements():
    element_filter = CandidateElementFilter(
        must_elements=["Y"],
        any_elements=["Na", "Mo", "Cl"],
        possible_elements=["C", "O"],
    )

    assert element_filter.matches({"Y", "Mo", "O"})
    assert element_filter.matches({"Y", "Na", "C", "O"})
    assert not element_filter.matches({"Y", "C", "O"})
    assert not element_filter.matches({"Y", "Mo", "O", "Fe"})
    assert element_filter.rejection_reason({"Y", "C", "O"}) == "failed_any"
    assert element_filter.rejection_reason({"Y", "Mo", "O", "Fe"}) == "outside_allowed"


def test_candidate_filter_rejects_elements_in_multiple_groups():
    with pytest.raises(ValueError, match="must/any"):
        CandidateElementFilter(must_elements=["Na"], any_elements=["Na", "Mo"])

    with pytest.raises(ValueError, match="any/possible"):
        CandidateElementFilter(any_elements=["Mo"], possible_elements=["Mo", "O"])


def test_candidate_filter_supports_boolean_any_expression():
    element_filter = CandidateElementFilter(
        must_elements=["Y"],
        any_expression="Na|(Cl&Mo)",
        possible_elements=["C", "O"],
    )

    assert element_filter.matches({"Y", "Na", "O"})
    assert element_filter.matches({"Y", "Cl", "Mo", "O"})
    assert not element_filter.matches({"Y", "Cl", "O"})


def test_filter_cif_paths_applies_element_filter_to_cif_files():
    element_filter = CandidateElementFilter(must_elements=["Bi", "Fe"], possible_elements=["O"])

    selection = filter_cif_paths(sorted(TEST_DATA.glob("*.cif")), element_filter)

    assert len(selection.selected_paths) == 3
    assert selection.rejected_counts == {
        "parse_error": 0,
        "missing_must": 0,
        "failed_any": 0,
        "outside_allowed": 0,
    }


def test_collect_database_cifs_uses_filter_query_elements_before_path_filtering(tmp_path):
    source_paths = sorted(TEST_DATA.glob("*.cif"))
    database = RecordingDatabase(source_paths)
    element_filter = CandidateElementFilter(must_elements=["Bi"], any_elements=["Fe"], possible_elements=["O"])

    raw_paths = collect_database_cifs([database], element_filter, tmp_path / "raw")
    selection = filter_cif_paths(raw_paths, element_filter)

    assert database.queries[0]["chemsys"] == {"Bi", "Fe", "O"}
    assert len(raw_paths) == 3
    assert len(selection.selected_paths) == 3
