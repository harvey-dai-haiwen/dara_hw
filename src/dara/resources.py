"""Resource budgeting for Dara workloads."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from typing import Literal

THREAD_ENV_VARS = (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "NUMEXPR_MAX_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
    "TBB_NUM_THREADS",
    "POLARS_MAX_THREADS",
)


def _get_int_env(name: str) -> int | None:
    raw_value = os.getenv(name)
    if raw_value in {None, ""}:
        return None
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc


def _get_float_env(name: str) -> float | None:
    raw_value = os.getenv(name)
    if raw_value in {None, ""}:
        return None
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number.") from exc


def _get_bool_env(name: str) -> bool | None:
    raw_value = os.getenv(name)
    if raw_value in {None, ""}:
        return None
    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class DaraResourceBudget:
    """CPU and memory limits shared by Dara search, BGMN, and Ray."""

    profile: Literal["auto", "small", "medium", "large"] = "auto"
    total_cpus: int | None = None
    memory_gb: float | None = None
    bgmn_threads: int | None = None
    max_bgmn_tasks: int | None = None
    native_threads: int | None = None
    peak_match_chunk_size: int | None = None
    peak_match_batch_size: int | None = None
    peak_match_max_pending_batches: int | None = None
    ray_object_store_memory_gb: float | None = None
    ray_local_mode: bool = False

    @classmethod
    def from_env(cls) -> DaraResourceBudget:
        """Build a budget from Dara environment variables and legacy aliases."""
        profile = os.getenv("DARA_RESOURCE_PROFILE", "auto").strip().lower()
        if profile not in {"auto", "small", "medium", "large"}:
            raise ValueError("DARA_RESOURCE_PROFILE must be one of auto, small, medium, or large.")

        legacy_parallel = _get_int_env("DARA_MAX_PARALLEL_REFINEMENTS")
        if legacy_parallel is None:
            legacy_parallel = _get_int_env("DARA_MAX_PARALLEL_JOBS")

        return cls(
            profile=profile,  # type: ignore[arg-type]
            total_cpus=_get_int_env("DARA_TOTAL_CPUS"),
            memory_gb=_get_float_env("DARA_MEMORY_GB"),
            bgmn_threads=_get_int_env("DARA_BGMN_THREADS"),
            max_bgmn_tasks=_get_int_env("DARA_MAX_BGMN_TASKS") or legacy_parallel,
            native_threads=_get_int_env("DARA_NATIVE_THREADS"),
            peak_match_chunk_size=_get_int_env("DARA_PEAK_MATCH_CHUNK_SIZE"),
            peak_match_batch_size=_get_int_env("DARA_PEAK_MATCH_BATCH_SIZE"),
            peak_match_max_pending_batches=_get_int_env("DARA_PEAK_MATCH_MAX_PENDING_BATCHES"),
            ray_object_store_memory_gb=_get_float_env("DARA_RAY_OBJECT_STORE_MEMORY_GB"),
            ray_local_mode=_get_bool_env("DARA_RAY_LOCAL_MODE") or False,
        ).resolve()

    @classmethod
    def make(cls, value: DaraResourceBudget | dict | None = None) -> DaraResourceBudget:
        """Normalize user-provided resource settings."""
        if value is None:
            return cls.from_env()
        if isinstance(value, DaraResourceBudget):
            return value.resolve()
        if isinstance(value, dict):
            return cls(**value).resolve()
        raise TypeError("resource_budget must be None, a dict, or DaraResourceBudget.")

    def resolve(self) -> DaraResourceBudget:
        """Fill unset values using conservative machine-aware defaults."""
        total_cpus = max(1, int(self.total_cpus or os.cpu_count() or 1))
        profile = self.profile
        if profile == "auto":
            if total_cpus <= 4 or (self.memory_gb is not None and self.memory_gb <= 16):
                profile = "small"
            elif total_cpus >= 48 and (self.memory_gb is None or self.memory_gb >= 128):
                profile = "large"
            else:
                profile = "medium"

        if profile == "small":
            default_bgmn_threads = min(2, total_cpus)
            default_max_bgmn_tasks = 1
            default_chunk_size = 10_000
            default_batch_size = 500
            default_pending = 2
        elif profile == "large":
            default_bgmn_threads = min(2, total_cpus)
            default_max_bgmn_tasks = max(1, total_cpus // max(1, default_bgmn_threads))
            default_chunk_size = 100_000
            default_batch_size = 2_000
            default_pending = max(2, min(32, default_max_bgmn_tasks * 2))
        else:
            default_bgmn_threads = min(2, max(1, total_cpus // 4) or 1)
            default_max_bgmn_tasks = max(1, total_cpus // max(1, default_bgmn_threads))
            default_chunk_size = 25_000
            default_batch_size = 1_000
            default_pending = max(2, min(8, default_max_bgmn_tasks * 2))

        bgmn_threads = min(total_cpus, max(1, int(self.bgmn_threads or default_bgmn_threads)))
        max_bgmn_tasks = max(1, int(self.max_bgmn_tasks or default_max_bgmn_tasks))
        native_threads = max(1, int(self.native_threads or 6))

        return replace(
            self,
            profile=profile,  # type: ignore[arg-type]
            total_cpus=total_cpus,
            bgmn_threads=bgmn_threads,
            max_bgmn_tasks=max_bgmn_tasks,
            native_threads=native_threads,
            peak_match_chunk_size=max(1, int(self.peak_match_chunk_size or default_chunk_size)),
            peak_match_batch_size=max(1, int(self.peak_match_batch_size or default_batch_size)),
            peak_match_max_pending_batches=max(1, int(self.peak_match_max_pending_batches or default_pending)),
        )

    @property
    def ray_num_cpus(self) -> int:
        """CPU capacity advertised to Ray for Dara tasks."""
        assert self.bgmn_threads is not None
        assert self.max_bgmn_tasks is not None
        return max(1, min(self.total_cpus or 1, self.bgmn_threads * self.max_bgmn_tasks))

    def apply_native_thread_limits(self) -> None:
        """Cap native numerical-library thread pools before heavy imports execute work."""
        assert self.native_threads is not None
        for variable in THREAD_ENV_VARS:
            os.environ[variable] = str(self.native_threads)


def init_ray_for_dara(resource_budget: DaraResourceBudget | dict | None = None) -> DaraResourceBudget:
    """Initialize Ray once with Dara's resource budget and return the resolved budget."""
    import ray

    budget = DaraResourceBudget.make(resource_budget)
    budget.apply_native_thread_limits()

    if not ray.is_initialized():
        ray_init_kwargs = {
            "num_cpus": budget.ray_num_cpus,
            "runtime_env": {"working_dir": None},
            "local_mode": budget.ray_local_mode,
        }
        if budget.ray_object_store_memory_gb is not None:
            ray_init_kwargs["object_store_memory"] = int(budget.ray_object_store_memory_gb * 1024**3)
        ray.init(**ray_init_kwargs)

    return budget
