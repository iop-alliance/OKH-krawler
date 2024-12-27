# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass

from krawl.fetcher.result import FetchResult
from krawl.model.hosting_unit import HostingUnitId


@dataclass(slots=True, frozen=True)
class FailedFetch:
    """The result of a failed fetch of an OSH projects meta-data."""
    hosting_unit_id: HostingUnitId
    error: Exception


class FetchListener:
    """Receives events of failed or successful fetches of OSH projects"""

    def fetched(self, fetch_result: FetchResult) -> None:
        pass

    def failed_fetch(self, failed_fetch: FailedFetch) -> None:
        pass
