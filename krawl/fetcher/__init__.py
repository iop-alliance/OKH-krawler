from __future__ import annotations

from collections.abc import Generator

from krawl.exceptions import FetcherException
from krawl.project import Project


class Fetcher:
    """Interface for fetching projects."""

    PLATFORM = None

    def fetch(self, id: str) -> Project:
        raise NotImplementedError()

    def fetch_all(self, start_over=True) -> Generator[Project, None, None]:
        raise NotImplementedError()

    def _parse_id(self, id: str) -> tuple[str, str]:
        splitted = id.split("/")
        if not len(splitted) == 3:
            raise FetcherException(f"invalid id '{id}'")
        platform, owner, name = splitted
        if platform != self.PLATFORM:
            raise FetcherException(f"'{self.PLATFORM}' fetcher cannot handle '{platform}'")
        return owner, name
