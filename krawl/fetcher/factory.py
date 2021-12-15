from __future__ import annotations

from typing import Generator

from krawl.exceptions import FetcherException
from krawl.fetcher import Fetcher
from krawl.fetcher.wikifactory import WikifactoryFetcher
from krawl.project import Project
from krawl.storage import FetcherStateStorage

# use dict for faster lookups
fetcher_classes = {
    WikifactoryFetcher.PLATFORM: WikifactoryFetcher,
}


class FetcherFactory:

    def __init__(self, state_storage: FetcherStateStorage, batch_size=10, timeout=10) -> None:
        self._fetchers = {}
        self._init_fetchers(state_storage, batch_size, timeout)

    def get_fetcher(self, id: str) -> Fetcher:
        platform = id.split("/")[0]
        if not platform in self._fetchers:
            raise FetcherException(f"no fetcher available for '{platform}'")
        return self._fetchers[platform]

    def get_fetchers(self) -> Generator[Fetcher, None, None]:
        for fetcher in self._fetchers.values():
            yield fetcher

    def fetch(self, id: str) -> Project:
        platform = id.split("/")[0]
        if not platform in self._fetchers:
            raise FetcherException(f"no fetcher available for '{platform}'")
        return self._fetchers[platform].fetch(id)

    def _init_fetchers(self, state_storage, batch_size, timeout):
        for fetcher_class in fetcher_classes.values():
            self._fetchers[fetcher_class.PLATFORM] = fetcher_class(state_storage, batch_size, timeout)


def available_fetchers() -> list[str]:
    return [fetcher for fetcher in fetcher_classes.keys()]


def is_fetcher_available(id: str) -> bool:
    platform = id.split("/")[0]
    return platform in fetcher_classes
