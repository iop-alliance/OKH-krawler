from __future__ import annotations

import re
from collections.abc import Mapping

from cleo import Command
from clikit.api.args.format import Option

from krawl.config import (CliConfigLoader, Config, MergedConfigLoader, YamlFileConfigLoader, get_assembled_schema,
                          iterate_schema)
from krawl.exceptions import ConfigException
from krawl.fetcher.factory import FetcherFactory
from krawl.repository.factory import ProjectRepositoryFactory


class KrawlCommand(Command):

    def option_int(self, key, default=None, min=None, max=None):
        value = self.option(key)
        if value is None:
            return default
        if isinstance(value, str):
            value = value.strip()
            if not value.isdigit():
                raise ValueError(f"'{key}' must be a number, got this instead: {value}")
            value = int(value)
        if not isinstance(value, int):
            raise ValueError()
        if min is not None and value < min:
            raise ValueError(f"{key} must be greater than {min}")
        if max is not None and value > max:
            raise ValueError(f"{key} must be lower than {max}")
        return value

    def _load_config_schema(self, enabled_repositories: list[str] = None, enabled_fetchers: list[str] = None) -> dict:
        fetchers_schema = FetcherFactory.get_config_schemas(enabled_fetchers)
        repositories_schema = ProjectRepositoryFactory.get_config_schemas(enabled_repositories)
        config_schema = get_assembled_schema(fetchers_schema, repositories_schema)
        return config_schema

    def _load_config(self, enabled_repositories: list[str], enabled_fetchers: list[str]) -> Config:
        config_schema = self._load_config_schema(enabled_repositories, enabled_fetchers)
        cli_options = self._get_options_from_schema(config_schema)

        # normalize and validate config
        cli_config_loader = CliConfigLoader(config_schema, cli_options)
        yaml_config_loader = YamlFileConfigLoader(config_schema, self.option("config"))
        # the order specifies the priority of the options (CLI before file)
        config = MergedConfigLoader(config_schema, cli_config_loader, yaml_config_loader).load()

        return config

    @staticmethod
    def _normalize_option_name(name: str) -> str:
        pattern = re.compile(r"[^a-z0-9]")
        return re.sub(pattern, "-", name)

    def _add_options_from_schema(self, schema: Mapping, prefix=None) -> None:
        for _, rule in iterate_schema(schema):
            meta = rule.get("meta", {})
            short_name = meta.get("short_name")
            long_name = meta.get("long_name")
            if not (short_name or long_name):
                continue
            if long_name:
                if prefix:
                    short_name = None
                    long_name = prefix + long_name
                long_name = self._normalize_option_name(long_name)
            description = meta.get("description")
            self._config.add_option(
                long_name=long_name,
                short_name=short_name,
                flags=Option.NO_VALUE if rule.get("type") == "boolean" else Option.REQUIRED_VALUE,
                description=description,
            )

    def _get_options_from_schema(self, schema, prefix=None) -> Mapping:
        c = Config()
        for key, rule in iterate_schema(schema):
            meta = rule.get("meta", {})
            short_name = meta.get("short_name")
            long_name = meta.get("long_name")
            if long_name:
                if prefix:
                    short_name = None
                    long_name = prefix + long_name
                long_name = self._normalize_option_name(long_name)
                c[key] = self.option(long_name)
            elif short_name:
                c[key] = self.option(short_name)
        return c
