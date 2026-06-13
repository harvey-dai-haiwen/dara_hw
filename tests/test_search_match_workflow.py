from pathlib import Path

from dara.search_match import (
    DaraSearchMatchConfig,
    ElementFilterConfig,
    MachineConfig,
    run_search_match,
)
from dara.search_match_cli import main as search_match_cli_main


REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_DATA = REPO_ROOT / "tests" / "test_data"


def test_run_search_match_dry_run_local_cifs_only(tmp_path):
    summary = run_search_match(
        DaraSearchMatchConfig(
            dara_root=REPO_ROOT,
            sample_path=TEST_DATA / "BiFeO3.xy",
            output_root=tmp_path / "run",
            databases=(),
            element_filter=ElementFilterConfig(must=("Bi", "Fe"), possible=("O",)),
            additional_cif_dirs=(TEST_DATA,),
            machine=MachineConfig(logical_threads=4, memory_gb=16, cpu_target_fraction=0.5),
            dry_run=True,
        ),
        database_objects=[],
    )

    assert summary["status"] == "planned"
    assert summary["databases"] == []
    assert summary["candidate_count_selected"] == 3
    assert summary["resource_budget"]["profile"] == "small"
    assert (tmp_path / "run" / "summary.json").exists()


def test_search_match_cli_dry_run_local_cifs_only(tmp_path):
    exit_code = search_match_cli_main(
        [
            "--dara-root",
            str(REPO_ROOT),
            "--xrd",
            str(TEST_DATA / "BiFeO3.xy"),
            "--output-root",
            str(tmp_path / "cli-run"),
            "--no-database",
            "--must-element",
            "Bi",
            "--must-element",
            "Fe",
            "--possible-element",
            "O",
            "--additional-cif-dir",
            str(TEST_DATA),
            "--logical-threads",
            "4",
            "--memory-gb",
            "16",
            "--cpu-target-fraction",
            "0.5",
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "cli-run" / "summary.json").exists()


def test_run_search_match_dry_run_with_pinned_cif(tmp_path):
    summary = run_search_match(
        DaraSearchMatchConfig(
            dara_root=REPO_ROOT,
            sample_path=TEST_DATA / "BiFeO3.xy",
            output_root=tmp_path / "pinned-run",
            databases=(),
            element_filter=ElementFilterConfig(must=("Bi", "Fe"), possible=("O",)),
            additional_cif_dirs=(TEST_DATA,),
            pinned_cifs=(TEST_DATA / "BiFeO3.cif",),
            machine=MachineConfig(logical_threads=4, memory_gb=16, cpu_target_fraction=0.5),
            dry_run=True,
        ),
        database_objects=[],
    )

    assert summary["status"] == "planned"
    assert summary["pinned_count"] == 1
    assert summary["candidate_count_selected"] == 3
    assert summary["candidate_count_searchable_selected"] == 2
    assert summary["structure_dedupe"]["searchable_duplicate_of_pinned_count"] == 1
    assert summary["pinned_selected_paths"][0].endswith("BiFeO3.cif")


def test_search_match_cli_accepts_pinned_cif(tmp_path):
    exit_code = search_match_cli_main(
        [
            "--dara-root",
            str(REPO_ROOT),
            "--xrd",
            str(TEST_DATA / "BiFeO3.xy"),
            "--output-root",
            str(tmp_path / "cli-pinned-run"),
            "--no-database",
            "--must-element",
            "Bi",
            "--must-element",
            "Fe",
            "--possible-element",
            "O",
            "--additional-cif-dir",
            str(TEST_DATA),
            "--pinned-cif",
            str(TEST_DATA / "BiFeO3.cif"),
            "--logical-threads",
            "4",
            "--memory-gb",
            "16",
            "--cpu-target-fraction",
            "0.5",
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "cli-pinned-run" / "summary.json").exists()
