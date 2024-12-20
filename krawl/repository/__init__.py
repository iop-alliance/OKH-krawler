from __future__ import annotations

from collections.abc import Generator

from krawl.project import Project


class ProjectRepository:
    """Interface for storing crawled projects metadata."""

    NAME = None
    CONFIG_SCHEMA = None

    def load(self, id) -> Project:
        raise NotImplementedError()

    def load_all(self, id) -> Generator[Project]:
        raise NotImplementedError()

    def store(self, project: Project) -> None:
        raise NotImplementedError()

    def contains(self, id: str) -> bool:
        raise NotImplementedError()

    def search(self,
               platform: str | None = None,
               owner: str | None = None,
               name: str | None = None) -> Generator[Project]:
        raise NotImplementedError()

    def delete(self, id: str) -> None:
        raise NotImplementedError()


class FetcherStateRepository:

    def load(self, fetcher: str) -> dict:
        raise NotImplementedError()

    def store(self, fetcher: str, state: dict) -> None:
        raise NotImplementedError()

    def delete(self, fetcher: str) -> bool:
        raise NotImplementedError()
