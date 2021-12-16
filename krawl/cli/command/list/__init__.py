from krawl.cli.command import KrawlCommand
from krawl.cli.command.list.fetchers import ListFetchersCommand


class ListCommand(KrawlCommand):
    """Fetch a project from a platform.

    list
    """

    commands = [
        ListFetchersCommand(),
    ]

    def handle(self):
        self.call("help", "list")
