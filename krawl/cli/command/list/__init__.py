from cleo import Command

from krawl.cli.command.list.fetchers import ListFetchersCommand


class ListCommand(Command):
    """Fetch a project from a platform.

    list
    """

    commands = [
        ListFetchersCommand(),
    ]

    def handle(self):
        self.call("help", "list")
