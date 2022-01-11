from __future__ import annotations

from collections.abc import Generator

from krawl.config import Config
from krawl.errors import FetcherError
from krawl.fetcher import Fetcher
from krawl.fetcher.github import GitHubFetcher
from krawl.fetcher.oshwa import OshwaFetcher
from krawl.fetcher.thingiverse import ThingiverseFetcher
from krawl.fetcher.wikifactory import WikifactoryFetcher
from krawl.project import Project, ProjectID
from krawl.repository import FetcherStateRepository

_fetcher_classes = {
    WikifactoryFetcher.NAME: WikifactoryFetcher,
    GitHubFetcher.NAME: GitHubFetcher,
    OshwaFetcher.NAME: OshwaFetcher,
    ThingiverseFetcher.NAME: ThingiverseFetcher,
}


class FetcherFactory:

    def __init__(self,
                 state_repository: FetcherStateRepository,
                 fetchers_config: Config,
                 enabled: list[str] = None) -> None:
        self._fetchers = {}
        self._enabled = enabled or list(_fetcher_classes.keys())

        for e in enabled:
            assert e in _fetcher_classes

        self._init_fetchers(state_repository, fetchers_config, enabled)

    @property
    def enabled(self) -> list[str]:
        return self._enabled

    @classmethod
    def get_config_schemas(cls, names: list[str] = None) -> dict:
        if not names:
            return {n: c.CONFIG_SCHEMA for n, c in _fetcher_classes.items()}
        schema = {}
        for name in names:
            if name not in _fetcher_classes:
                raise FetcherError(
                    f"no fetcher available for '{name}', available are: {', '.join(_fetcher_classes.keys())}")
            schema[name] = _fetcher_classes[name].CONFIG_SCHEMA
        return schema

    def get_enabled_config_schemas(self) -> dict:
        return {e: _fetcher_classes[e].CONFIG_SCHEMA for e in self._enabled}

    @classmethod
    def list_available_fetchers(cls) -> list[str]:
        return list(_fetcher_classes)

    @classmethod
    def is_fetcher_available(cls, name: str) -> bool:
        return name in _fetcher_classes

    def get(self, name: str) -> Fetcher:
        if name not in _fetcher_classes:
            raise FetcherError(
                f"no fetcher available for '{name}', available are: {', '.join(_fetcher_classes.keys())}")
        if name not in self._fetchers:
            raise FetcherError(f"fetcher '{name}' is not enabled")
        return self._fetchers[name]

    def get_all(self) -> Generator[Fetcher, None, None]:
        for fetcher in self._fetchers.values():
            yield fetcher

    def fetch(self, id: ProjectID) -> Project:
        """Call `fetch` function on fitting fetcher."""
        if id.platform not in self._fetchers:
            raise FetcherError(f"no fetcher available for '{id.platform}'")
        if id.platform not in self._fetchers:
            raise FetcherError(f"fetcher '{id.platform}' is not enabled")
        return self._fetchers[id.platform].fetch(id)

    def fetch_all(self, start_over=True) -> Generator[Project, None, None]:
        """Call `fetch_all` function on all enabled fetchers."""
        # TODO: should be parallelized
        for fetcher in self._fetchers.values():
            yield from fetcher.fetch_all(start_over=start_over)

    def _init_fetchers(self, state_repository, fetchers_config: Config, enabled: list[str]):
        for name, fetcher_class in _fetcher_classes.items():
            if name in enabled:
                self._fetchers[name] = fetcher_class(state_repository, fetchers_config[name])
