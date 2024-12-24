from __future__ import annotations

from enum import StrEnum

from krawl.fetcher import FailedFetch, FetchListener, FetchResult
from krawl.model.hosting_unit import HostingUnitId
from krawl.model.project import Project


class Status(StrEnum):
    UNKNOWN = "unknown"
    OK = "ok"
    FAILED = "failed"

    def __str__(self) -> str:
        return self.name


class Reporter(FetchListener):
    """Interface for creating a fetching report."""

    def add(self,
            hosting_unit_id: HostingUnitId,
            status: Status,
            reasons: list[str] = None,
            project: Project = None) -> None:
        """Add an entry to the report."""
        raise NotImplementedError()

    def close(self) -> None:
        """Closes the underlying resources."""
        raise NotImplementedError()

    def __del__(self):
        self.close()

    def fetched(self, fetch_result: FetchResult) -> None:
        self.add(fetch_result.data_set.hosting_unit_id, Status.OK)

    def failed_fetch(self, failed_fetch: FailedFetch) -> None:
        self.add(failed_fetch.data_set.hosting_unit_id, Status.FAILED, str(failed_fetch.error))
