from krawl.cli.command import KrawlCommand
from krawl.fetcher.factory import available_fetchers


class ListFetchersCommand(KrawlCommand):
    """List available fetchers.

    fetchers
    """

    def handle(self):
        for name in available_fetchers():
            self.line(name)
