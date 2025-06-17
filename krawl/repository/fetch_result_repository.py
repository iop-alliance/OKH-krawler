# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from krawl.fetcher.event import FailedFetch, FetchListener
from krawl.fetcher.result import FetchResult


class FetchResultRepository(FetchListener):
    """Interface for storing crawled projects metadata."""

    CONFIG_SCHEMA: dict

    def store_fetched(self, fetch_result: FetchResult) -> None:
        raise NotImplementedError()

    def store_final(self, fetch_result: FetchResult, rdf_normalized_toml_content: str, rdf_meta_content: str,
                    rdf_content: str) -> None:
        raise NotImplementedError()

    def fetched(self, fetch_result: FetchResult) -> None:
        self.store_fetched(fetch_result)

    def failed_fetch(self, failed_fetch: FailedFetch) -> None:
        pass
