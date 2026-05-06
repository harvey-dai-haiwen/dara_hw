from __future__ import annotations

import os.path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from dara.resources import DaraResourceBudget


class DaraServerSettings(BaseSettings):
    """
    Settings for the Dara server.

    Attributes:
        host (str): The host address for the server.
            Default is "127.0.0.1".
        port (int): The port on which the server will run.
            Default is 8898.
        database_backend (Literal["monty", "mongodb"]): The backend
            to use for the database. Default is "monty".
        mongodb_host (str): Host for MongoDB. Used only if database_backend
            is "mongodb". Default is "localhost".
        mongodb_port (int): Port for MongoDB. Used only if database_backend
            is "mongodb". Default is 27017.
        mongodb_database (str): Database name for MongoDB. Used only if
            database_backend is "mongodb". Default is "dara_server".
        mongodb_username (str | None): Username for MongoDB. Used only if
            database_backend is "mongodb". Default is None.
        mongodb_password (str | None): Password for MongoDB. Used only if
            database_backend is "mongodb". Default is None.
        montydb_path (str): Path for MontyDB database. Used only if
            database_backend is "monty". Default is "~/.dara-server/montydb".
    """

    model_config = SettingsConfigDict(
        env_prefix="dara_server_",
        cli_parse_args=True,
        cli_ignore_unknown_args=True,
    )


    host: str = Field(
        default="127.0.0.1",
        description="The host address for the server."
    )

    port: int = Field(
        default=8898,
        description="The port on which the server will run."
    )

    database_backend: Literal["monty", "mongodb"] = Field(
        default="monty",
        description="The backend to use for the database."
    )

    mongodb_host: str = Field(
        default="localhost",
        description='Host for MongoDB. Used only if database_backend is "mongodb".'
    )

    mongodb_port: int = Field(
        default=27017,
        description='Port for MongoDB. Used only if database_backend is "mongodb".'
    )

    mongodb_database: str = Field(
        default="dara_server",
        description='Database name for MongoDB. Used only if database_backend is "mongodb".'
    )

    mongodb_username: str | None = Field(
        default=None,
        description='Username for MongoDB. Used only if database_backend is "mongodb".'
    )

    mongodb_password: str | None = Field(
        default=None,
        description='Password for MongoDB. Used only if database_backend is "mongodb".'
    )

    montydb_path: str = Field(
        default=os.path.expanduser("~/.dara-server/montydb"),
        description='Path for MontyDB database. Used only if database_backend is "monty".'
    )

    resource_profile: Literal["auto", "small", "medium", "large"] = Field(
        default="auto",
        description="Resource profile for Dara search jobs.",
    )
    total_cpus: int | None = Field(
        default=None,
        description="Total CPU budget exposed to Ray for Dara jobs.",
    )
    memory_gb: float | None = Field(
        default=None,
        description="Approximate memory budget in GB.",
    )
    bgmn_threads: int | None = Field(
        default=None,
        description="Threads used inside each BGMN process.",
    )
    max_bgmn_tasks: int | None = Field(
        default=None,
        description="Maximum concurrent BGMN refinement processes.",
    )
    native_threads: int | None = Field(
        default=None,
        description="Thread cap for native numerical libraries.",
    )
    peak_match_chunk_size: int | None = Field(
        default=None,
        description="Maximum upper-triangle phase pairs materialized per peak-matching chunk.",
    )
    peak_match_batch_size: int | None = Field(
        default=None,
        description="Number of peak comparisons per Ray peak-matching task.",
    )
    peak_match_max_pending_batches: int | None = Field(
        default=None,
        description="Maximum pending peak-matching Ray tasks kept in memory.",
    )
    ray_object_store_memory_gb: float | None = Field(
        default=None,
        description="Optional Ray object store memory cap in GB.",
    )

    def __init__(self, **values):
        super().__init__(**values)
        # Ensure montydb_path directory exists if using monty backend
        if self.database_backend == "monty" and self.montydb_path:
            dir_path = os.path.dirname(self.montydb_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)

    def resource_budget(self) -> DaraResourceBudget:
        """Build the resource budget used by the server worker."""
        return DaraResourceBudget(
            profile=self.resource_profile,
            total_cpus=self.total_cpus,
            memory_gb=self.memory_gb,
            bgmn_threads=self.bgmn_threads,
            max_bgmn_tasks=self.max_bgmn_tasks,
            native_threads=self.native_threads,
            peak_match_chunk_size=self.peak_match_chunk_size,
            peak_match_batch_size=self.peak_match_batch_size,
            peak_match_max_pending_batches=self.peak_match_max_pending_batches,
            ray_object_store_memory_gb=self.ray_object_store_memory_gb,
        ).resolve()


def get_dara_server_settings() -> DaraServerSettings:
    """Get the settings for the Dara server."""
    return DaraServerSettings()  # type: ignore[return-value]
