from cleo import Command

from krawl.cli.command.fetch.wikifactory import FetchWikifactoryCommand


class FetchCommand(Command):
    """Fetch a project from a platform.

    fetch
        {url : URL to fetch}
    """

    commands = [
        FetchWikifactoryCommand(),
    ]

    def handle(self):
        self.call("help", "fetch")
