# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import re
from collections.abc import Mapping

from cleo import Command
from clikit.api.args.format import Option

from krawl.config import (CliConfigLoader, Config, KrawlerConfigLoader, YamlFileConfigLoader, get_assembled_schema,
                          iterate_schema)
from krawl.fetcher.factory import FetcherFactory
from krawl.model.hosting_id import HostingId
from krawl.repository import ProjectRepositoryType
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

    def _load_config_schema(self,
                            enabled_repositories: list[ProjectRepositoryType] | None = None,
                            enabled_fetchers: list[HostingId] | None = None) -> dict:
        fetchers_schema: dict[HostingId, dict] = FetcherFactory.get_config_schemas(enabled_fetchers)
        repositories_schema: dict[ProjectRepositoryType, dict] = ProjectRepositoryFactory.get_config_schemas(enabled_repositories)
        config_schema: dict = get_assembled_schema(fetchers_schema, repositories_schema)
        return config_schema

    def _load_config(self, enabled_repositories: list[ProjectRepositoryType] | None,
                     enabled_fetchers: list[HostingId] | None) -> Config:
        config_schema = self._load_config_schema(enabled_repositories, enabled_fetchers)
        cli_options = self._get_options_from_schema(config_schema)

        # normalize and validate config
        cli_config_loader = CliConfigLoader(config_schema, cli_options)
        yaml_config_loader = YamlFileConfigLoader(config_schema, self.option("config"))
        # the order specifies the priority of the options (CLI before file)
        config = KrawlerConfigLoader(config_schema, cli_config_loader, yaml_config_loader).load()

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
        config = Config()
        for key, rule in iterate_schema(schema):
            meta = rule.get("meta", {})
            short_name = meta.get("short_name")
            long_name = meta.get("long_name")
            if long_name:
                if prefix:
                    short_name = None
                    long_name = prefix + long_name
                long_name = self._normalize_option_name(long_name)
                config[key] = self.option(long_name)
            elif short_name:
                config[key] = self.option(short_name)
        return config
