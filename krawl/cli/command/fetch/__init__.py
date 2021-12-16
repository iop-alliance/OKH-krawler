from krawl.cli.command import KrawlCommand
from krawl.cli.command.fetch.fetcher import FetcherXCommand
from krawl.cli.command.fetch.url import FetchURLCommand
from krawl.fetcher.factory import available_fetchers


def _dynamic_fetcher_commands() -> list[KrawlCommand]:
    return [FetcherXCommand(fetcher) for fetcher in available_fetchers()]


class FetchCommand(KrawlCommand):
    """Fetch a project from a platform.

    fetch
    """

    commands = [
        FetchURLCommand(),
    ] + _dynamic_fetcher_commands()

    def handle(self):
        self.call("help", "fetch")
