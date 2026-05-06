import numpy as np

from dara.resources import DaraResourceBudget
from dara.search import tree as tree_module
from dara.search.peak_matcher import PeakMatcher


def _serial_peak_matching(
    peak_calcs,
    peak_obs,
    return_type="PeakMatcher",
    batch_size=100,
    score_kwargs=None,
    max_pending_batches=None,
    resource_budget=None,
):
    if isinstance(peak_obs, np.ndarray):
        peak_obs = [peak_obs] * len(peak_calcs)

    results = []
    for peak_calc, peak_obs_item in zip(peak_calcs, peak_obs, strict=True):
        matcher = PeakMatcher(peak_calc, peak_obs_item)
        if return_type == "PeakMatcher":
            results.append(matcher)
        elif return_type == "score":
            results.append(matcher.score(**(score_kwargs or {})))
        elif return_type == "jaccard":
            results.append(matcher.jaccard_index())
        else:
            raise ValueError(f"Unknown return type {return_type}")
    return results


def _legacy_distance_matrix(peaks):
    size = len(peaks)
    similarities = []
    for peak_calc in peaks:
        for peak_obs in peaks:
            similarities.append(PeakMatcher(peak_calc, peak_obs).jaccard_index())
    distance_matrix = 1 - np.array(similarities).reshape(size, size)
    return (distance_matrix + distance_matrix.T) / 2


def test_chunked_pairwise_matches_legacy_ordered_global_matrix(monkeypatch):
    peaks = [
        np.array([[10.0, 100.0], [20.0, 40.0]]),
        np.array([[10.05, 90.0], [30.0, 10.0]]),
        np.array([[15.0, 80.0], [20.05, 20.0]]),
        np.array([[40.0, 50.0], [50.0, 10.0]]),
    ]
    budget = DaraResourceBudget(
        total_cpus=4,
        bgmn_threads=2,
        max_bgmn_tasks=1,
        peak_match_chunk_size=2,
        peak_match_batch_size=2,
        peak_match_max_pending_batches=1,
    ).resolve()

    monkeypatch.setattr(tree_module, "batch_peak_matching", _serial_peak_matching)

    actual = tree_module.pairwise_jaccard_distance_matrix(peaks, resource_budget=budget)
    expected = _legacy_distance_matrix(peaks)

    np.testing.assert_allclose(actual, expected, atol=1e-7)


def test_pairwise_chunk_size_limits_materialized_pairs(monkeypatch):
    peaks = [np.array([[float(i), 1.0]]) for i in range(6)]
    observed_batch_sizes = []

    def serial_with_observation(*args, **kwargs):
        observed_batch_sizes.append(len(args[0]))
        return _serial_peak_matching(*args, **kwargs)

    budget = DaraResourceBudget(
        total_cpus=4,
        bgmn_threads=2,
        max_bgmn_tasks=1,
        peak_match_chunk_size=3,
        peak_match_batch_size=10,
    ).resolve()
    monkeypatch.setattr(tree_module, "batch_peak_matching", serial_with_observation)

    tree_module.pairwise_jaccard_distance_matrix(peaks, resource_budget=budget)

    assert max(observed_batch_sizes) == 6  # two ordered comparisons for each upper-triangle pair
