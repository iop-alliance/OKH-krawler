from __future__ import annotations

from krawl.fetcher import FailedFetch, FetchListener, FetchResult


class FetchResultRepository(FetchListener):
    """Interface for storing crawled projects metadata."""

    CONFIG_SCHEMA = None

    def store(self, fetch_result: FetchResult) -> None:
        raise NotImplementedError()

    def fetched(self, fetch_result: FetchResult) -> None:
        self.store(fetch_result)

    def failed_fetch(self, failed_fetch: FailedFetch) -> None:
        pass
