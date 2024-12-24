from __future__ import annotations

from collections.abc import Generator

from krawl.config import Config
from krawl.errors import FetcherError
from krawl.fetcher import Fetcher
from krawl.fetcher.event import FetchListener
from krawl.fetcher.github import GitHubFetcher
from krawl.fetcher.oshwa import OshwaFetcher
from krawl.fetcher.result import FetchResult
from krawl.fetcher.thingiverse import ThingiverseFetcher
from krawl.model.hosting_id import HostingId
from krawl.model.project_id import ProjectId
from krawl.repository import FetcherStateRepository
from krawl.repository.fetch_result_repository import FetchResultRepository
from krawl.repository.fetch_result_repository_workdir import FetchResultRepositoryWorkdir

_fetcher_classes = {
    GitHubFetcher.HOSTING_ID: GitHubFetcher,
    OshwaFetcher.HOSTING_ID: OshwaFetcher,
    ThingiverseFetcher.HOSTING_ID: ThingiverseFetcher,
}


class FetcherFactory:

    def __init__(self,
                 repository_config: Config,
                 state_repository: FetcherStateRepository,
                 fetchers_config: Config,
                 enabled: list[HostingId] = None) -> None:
        self._fetchers = {}
        self._enabled = enabled or list(_fetcher_classes.keys())

        for e in enabled:
            assert e in _fetcher_classes

        self._init_fetchers(repository_config, state_repository, fetchers_config, enabled)

    @property
    def enabled(self) -> list[HostingId]:
        return self._enabled

    @classmethod
    def get_config_schemas(cls, hosting_ids: list[HostingId] = None) -> dict:
        if not hosting_ids:
            return {n: c.CONFIG_SCHEMA for n, c in _fetcher_classes.items()}
        schema = {}
        for hosting_id in hosting_ids:
            if hosting_id not in _fetcher_classes:
                raise FetcherError(
                    f"no fetcher available for '{hosting_id}', available are: {', '.join(_fetcher_classes.keys())}")
            schema[hosting_id] = _fetcher_classes[hosting_id].CONFIG_SCHEMA
        return schema

    def get_enabled_config_schemas(self) -> dict:
        return {e: _fetcher_classes[e].CONFIG_SCHEMA for e in self._enabled}

    @classmethod
    def list_available_fetchers(cls) -> list[HostingId]:
        return list(_fetcher_classes)

    @classmethod
    def is_fetcher_available(cls, hosting_id: HostingId) -> bool:
        return hosting_id in _fetcher_classes

    def get(self, hosting_id: HostingId) -> Fetcher:
        if hosting_id not in _fetcher_classes:
            raise FetcherError(
                f"no fetcher available for '{hosting_id}', available are: {', '.join(_fetcher_classes.keys())}")
        if hosting_id not in self._fetchers:
            raise FetcherError(f"fetcher '{hosting_id}' is not enabled")
        return self._fetchers[hosting_id]

    def get_all(self) -> Generator[Fetcher]:
        yield from self._fetchers.values()

    def fetch(self, project_id: ProjectId) -> FetchResult:
        """Call `fetch` function on fitting fetcher."""
        # TODO PRIORITY:LOW Also parsed within the individual fetcher. Maybe try to parse only once
        hosting_id = HostingId.from_url(project_id.uri)
        if hosting_id not in self._fetchers:
            raise FetcherError(
                f"No fetcher available for '{hosting_id}', available are: {', '.join(_fetcher_classes.keys())}")
        return self._fetchers[hosting_id].fetch(project_id)

    def fetch_all(self, start_over=True) -> Generator[FetchResult]:
        """Call `fetch_all` function on all enabled fetchers."""
        # TODO: should be parallelized
        for fetcher in self._fetchers.values():
            yield from fetcher.fetch_all(start_over=start_over)

    def add_fetch_listener(self, listener: FetchListener) -> None:
        for fetcher in self._fetchers.values():
            fetcher.add_fetch_listener(listener)

    def _init_fetchers(self, repository_config: Config, state_repository, fetchers_config: Config,
                       enabled: list[HostingId]):
        fetch_listener: FetchResultRepository = FetchResultRepositoryWorkdir(repository_config.file)
        for hosting_id, fetcher_class in _fetcher_classes.items():
            if hosting_id in enabled:
                fetcher = fetcher_class(state_repository, fetchers_config[hosting_id])
                fetcher.add_fetch_listener(fetch_listener)
                self._fetchers[hosting_id] = fetcher
