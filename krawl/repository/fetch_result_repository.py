# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from krawl.fetcher.event import FailedFetch, FetchListener
from krawl.fetcher.result import FetchResult


class FetchResultRepository(FetchListener):
    """Interface for storing crawled projects metadata."""

    CONFIG_SCHEMA: dict

    def store(self, fetch_result: FetchResult) -> None:
        raise NotImplementedError()

    def fetched(self, fetch_result: FetchResult) -> None:
        self.store(fetch_result)

    def failed_fetch(self, failed_fetch: FailedFetch) -> None:
        pass
