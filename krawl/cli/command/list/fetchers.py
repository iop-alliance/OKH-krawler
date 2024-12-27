# SPDX-FileCopyrightText: 2021 Andre Lehmann <aisberg@posteo.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from krawl.cli.command import KrawlCommand
from krawl.fetcher.factory import FetcherFactory


class ListFetchersCommand(KrawlCommand):
    """List available fetchers.

    fetchers
    """

    def handle(self):
        for name in FetcherFactory.list_available_fetchers():
            self.line(name)
