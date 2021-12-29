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
