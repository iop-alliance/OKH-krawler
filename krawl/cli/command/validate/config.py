from __future__ import annotations

from pathlib import Path

from krawl.cli.command import KrawlCommand
from krawl.config import KrawlerConfigLoader, YamlFileConfigLoader
from krawl.errors import ConfigError


class ValidateConfigCommand(KrawlCommand):
    """Validate a given configuration. Non-zero return codes indicate an error.

    config
        {file : Config file to validate}
        {--q|quiet : Do not print reasons in case of invalid config}
    """

    def handle(self):
        path = Path(self.argument("file"))
        quiet = self.option("quiet")

        if not path.exists():
            raise FileNotFoundError(f"'{path}' doesn't exist")
        if not path.is_file():
            raise OSError(f"'{path}' is not a file")

        try:
            config_schema = self._load_config_schema()
            yaml_config_loader = YamlFileConfigLoader(config_schema, path)
            _ = KrawlerConfigLoader(config_schema, yaml_config_loader).load()
        except ConfigError as e:
            if not quiet:
                for r in e.reasons:
                    self.line(r)
            return 1

        return 0
