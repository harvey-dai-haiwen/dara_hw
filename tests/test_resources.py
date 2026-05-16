from dara.resources import DaraResourceBudget
from dara.search.tree import get_max_parallel_refinements
from dara.server.setting import DaraServerSettings


def test_small_budget_defaults_to_one_bgmn_task():
    budget = DaraResourceBudget(total_cpus=4, memory_gb=16).resolve()

    assert budget.profile == "small"
    assert budget.bgmn_threads == 2
    assert budget.max_bgmn_tasks == 1
    assert budget.ray_num_cpus == 2


def test_explicit_bgmn_budget_controls_refinement_parallelism():
    budget = DaraResourceBudget(
        total_cpus=64,
        bgmn_threads=4,
        max_bgmn_tasks=12,
    ).resolve()

    assert budget.ray_num_cpus == 48
    assert get_max_parallel_refinements({"n_threads": 4}, budget) == 12


def test_bgmn_threads_do_not_exceed_total_cpu_budget():
    budget = DaraResourceBudget(total_cpus=2, bgmn_threads=4, max_bgmn_tasks=1).resolve()

    assert budget.bgmn_threads == 2
    assert budget.ray_num_cpus == 2


def test_legacy_parallel_env_maps_to_max_bgmn_tasks(monkeypatch):
    monkeypatch.setenv("DARA_MAX_PARALLEL_REFINEMENTS", "3")
    monkeypatch.setenv("DARA_BGMN_THREADS", "2")
    monkeypatch.setenv("DARA_TOTAL_CPUS", "8")

    budget = DaraResourceBudget.from_env()

    assert budget.bgmn_threads == 2
    assert budget.max_bgmn_tasks == 3
    assert budget.ray_num_cpus == 6


def test_server_settings_build_resource_budget(tmp_path):
    settings = DaraServerSettings(
        montydb_path=str(tmp_path / "montydb"),
        resource_profile="small",
        total_cpus=4,
        bgmn_threads=2,
        max_bgmn_tasks=1,
    )

    budget = settings.resource_budget()

    assert budget.profile == "small"
    assert budget.bgmn_threads == 2
    assert budget.max_bgmn_tasks == 1
