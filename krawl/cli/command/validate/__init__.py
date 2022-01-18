from krawl.cli.command import KrawlCommand
from krawl.cli.command.validate.config import ValidateConfigCommand
from krawl.cli.command.validate.manifest import ValidateManifestCommand


class ValidateCommand(KrawlCommand):
    """Validate resources.

    validate
    """

    commands = [
        ValidateConfigCommand(),
        ValidateManifestCommand(),
    ]

    def handle(self):
        self.call("help", "validate")
