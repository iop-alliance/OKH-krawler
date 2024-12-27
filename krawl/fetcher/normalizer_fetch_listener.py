# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from krawl.fetcher.event import FailedFetch, FetchListener
from krawl.fetcher.result import FetchResult


class NormalizerFetchListener(FetchListener):
    """Normalizes fetch results and then stores them as OKH manifest files.
    NOTE We do not implement this, because we'd rather do this external to this krawler, maybe in okh-tool."""

    def fetched(self, fetch_result: FetchResult) -> None:
        pass

    def failed_fetch(self, failed_fetch: FailedFetch) -> None:
        pass
