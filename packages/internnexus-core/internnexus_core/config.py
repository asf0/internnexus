"""Shared pydantic-settings building blocks for backend and pipeline configs."""

from __future__ import annotations

from functools import lru_cache
from typing import Callable, Protocol, cast

from pydantic_settings import BaseSettings


class PostgresSettingsMixin(BaseSettings):
    """Postgres connection fields shared by every service Settings class."""

    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int

    @property
    def resolved_database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


def make_settings_loader[SettingsT: BaseSettings](settings_cls: type[SettingsT]) -> Callable[[], SettingsT]:
    """Build the cached zero-arg settings loader used as `get_settings`.

    BaseSettings resolves required fields from the environment at runtime;
    the cast presents the class constructor as a zero-arg factory for static
    checking.
    """

    class _SettingsFactory(Protocol):
        def __call__(self) -> SettingsT: ...

    settings_factory = cast(_SettingsFactory, settings_cls)

    @lru_cache
    def get_settings() -> SettingsT:
        return settings_factory()

    return get_settings
