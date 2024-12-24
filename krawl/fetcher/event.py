from __future__ import annotations

from dataclasses import dataclass

from krawl.fetcher.result import FetchResult
from krawl.model.hosting_unit import HostingUnitId


@dataclass(slots=True, frozen=True)
class FailedFetch:
    """The result of a failed fetch of an OSH projects meta-data."""
    hosting_unit_id: HostingUnitId = None
    error: Exception = None


class FetchListener:
    """Receives events of failed or successful fetches of OSH projects"""

    def fetched(self, fetch_result: FetchResult) -> None:
        pass

    def failed_fetch(self, failed_fetch: FailedFetch) -> None:
        pass
