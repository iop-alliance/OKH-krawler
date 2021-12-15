from cleo import Command

from krawl.fetcher.factory import FetcherFactory


class ListFetchersCommand(Command):
    """List available fetchers.

    fetchers
    """

    def handle(self):
        fetcher_factory = FetcherFactory(None)
        for fetcher in fetcher_factory.get_fetchers():
            self.line(fetcher.PLATFORM)
