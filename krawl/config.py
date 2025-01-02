# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2021 Alec Hanefeld <alec@konek.to>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""This module takes care of loading, normalizing and validating configurations
from different sources and merging them together.

It offer following features:
    - Loading from different sources such as YAML config file, CLI and
      environment variables
    - A single (cerberus) schema that is used to normalize/validate various
      configuration sources
    - Normalization/Validation for each source, so users can easily pin-point
      config errors
"""

from __future__ import annotations

from collections.abc import Generator, Mapping, MutableMapping
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from cerberus import TypeDefinition, Validator
from cerberus.errors import REQUIRED_FIELD, BasicErrorHandler, ValidationError
from str_to_bool import str_to_bool

from .errors import ConfigError, NotOverriddenError

# schema for normalization/validation
# see: https://docs.python-cerberus.org/en/stable/index.html
BASE_SCHEMA = {
    "database": {
        "type": "dict",
        "default": {},
        "meta": {
            "long_name": "db",
        },
        "schema": {
            "type": {
                "type": "string",
                "coerce": "strip_str",
                "default": "file",
                "allowed": ["file"],
                "meta": {
                    "long_name": "type",
                    "description": "Type of database to use. (available: file)"
                },
            },
            "path": {
                "type": "path",
                "default": Path("./workdir"),
                "nullable": False,
                "empty": False,
                "meta": {
                    "long_name": "path",
                    "description": "Database path"
                },
            },
        },
    },
    "user_agent": {
        "type": "string",
        "coerce": "strip_str",
        "default": "OKH crawler github.com/iop-alliance/OpenKnowHow",
        "nullable": False,
        "empty": False,
        "meta": {
            # used in CLI
            "long_name": "user-agent",
            "description": "Agent name used for requesting remote resources"
        },
    },
    "repositories": {
        "type": "dict",
        "default": {},
        # defined by the individual repositories
        "schema": {},
    },
    "fetchers": {
        "type": "dict",
        "default": {},
        # defined by the individual fetchers
        "schema": {
            "defaults": {
                "type": "dict",
                "default": {},
                "meta": {
                    "long_name": "fetchers",
                },
                "schema": {
                    "timeout": {
                        "type": "integer",
                        "nullable": True,
                        "min": 1,
                        "meta": {
                            "long_name": "timeout",
                            "description": "Max seconds to wait for a not responding service"
                        }
                    },
                    "retries": {
                        "type": "integer",
                        "nullable": True,
                        "min": 0,
                        "meta": {
                            "long_name": "retries",
                            "description": "Number of retries of requests in cases of network errors"
                        }
                    },
                },
            }
        },
    },
}

# represents a missing option
missing = type("MissingType", (), {"__repr__": lambda x: "missing"})()


def get_assembled_schema(fetchers_schema, repositories_schema):
    full_schema = deepcopy(BASE_SCHEMA)
    full_schema["fetchers"]["schema"].update(fetchers_schema)
    full_schema["repositories"]["schema"].update(repositories_schema)
    return full_schema


def _flatten_list(*list_: str | list) -> list:
    """Flatten a nested list.

    Args:
        element (str | list): A nested list to be flattened (or a single item).

    Returns:
        list: A recursively flattened list.
    """
    if not list_:
        return []
    flattened = []
    for item in list_:
        if isinstance(item, list):
            flattened.extend(_flatten_list(item))
        else:
            flattened.append(item)
    return flattened


def _flat_name(*args: str | list, separator="_", uppercase=False) -> str:
    """Turn a list of names into a flat name.

    Args:
        *args (str or list): Names to be turned into a flat name.
        separator (str): Separator used to separate each name component. Defaults to "_".
        uppercase (bool, optional): [description]. Defaults to False.

    Returns:
        str: A flat name with underscore used as a delimiter.
    """
    components = [item for item in _flatten_list(*args) if len(item) > 0]
    flat_name = separator.join(components)
    if uppercase:
        flat_name = flat_name.upper()
    return flat_name


def iterate_schema(schema: Mapping,
                   _key_path: list[str] | None = None,
                   _long_name_list: list[str] | None = None) -> Generator[tuple[list[str], Mapping]]:
    """Iterate over a schema.

    Args:
        schema (Mapping): Schema to be iterated over.
        _key_path (list, optional): Path of the current key (used in recursive call).

    Yields:
        Tuple: Tuple of key path and the associate rule.
    """
    key_path = _key_path or []
    long_name_list = _long_name_list or []
    for key, rules in schema.items():
        long_name = rules.get("meta", {}).get("long_name")
        if rules["type"] == "dict" and "schema" in rules:
            # iterate sub schema
            yield from iterate_schema(rules["schema"], key_path + [key], long_name_list + [long_name])
        else:
            rules = deepcopy(rules)
            if long_name:
                long_name = "-".join([n for n in long_name_list + [long_name] if n])
                rules["meta"]["long_name"] = long_name
            yield (key_path + [key], rules)


def validate(config: Mapping, schema: Mapping, middle_stage=False) -> tuple[Mapping | None, list[str]]:
    """Normalize and validate a config against a given schema.

    Args:
        config (Mapping): Config to normalize and validate.
        schema (Mapping): Schema used for validation.
        middle_stage (bool): If True, default values and 'required' checks are ignored.

    Returns:
        tuple(Mapping | None, list[str]): Tuple of normalized/validated config and
            reasons why the validation failed.
    """
    validator = ConfigValidator(schema, ignore_defaults=middle_stage)
    reasons = []
    if not validator.validate(config, update=middle_stage):
        errors = validator.errors
        for error in errors:
            path = ".".join(error["path"])
            # missing option error
            if error["code"] == 0x02:
                reasons.append(f"missing option '{path}'.")
            else:
                reasons.append(f"invalid option '{path}': {error['msg']}")

    if reasons:
        return None, reasons
    return validator.document, reasons


def effective_config_info(config: Config) -> Generator[str]:
    redacted_value = "X" * 20
    for key_path, rules in iterate_schema(BASE_SCHEMA):
        name = _flat_name(key_path, separator=".")
        # redact sensitive information
        redacted = rules.get("meta", {}).get("redact_log", False)
        if redacted:
            value = redacted_value
        else:
            value = config[key_path]
        yield f"{name}={value}"


class Config(MutableMapping):
    """Config data model.

    The model has certain superpowers when it comes to data access. For example
    the following access methods are equivalent:
        - config["foo"]["bar"]["baz"]
        - config[["foo", "bar", "baz"]]
        - config.foo.bar.baz

    Values can be set in the initialization or using the setter:
        - config["foo"] = {"bar": {"baz": "abc"}}
        - config.foo = {"bar": {"baz": "abc"}}
        - config[["foo", "bar", "baz"]] = "abc"

    Args:
        mapping (Mapping): Initial value of the config.
    """

    def __init__(self, mapping: Mapping | None = None) -> None:
        super().__setattr__("_mapping", {})
        self.update(mapping or {})

    def __getitem__(self, key):
        if isinstance(key, list):
            parent = key[:-1]
            key = key[-1]
            branch = self
            for p in parent:
                if not (p in branch and isinstance(branch[p], Mapping)):
                    raise KeyError(p)
                branch = branch[p]
            return branch[key]
        return self._mapping[key]

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)  # pylint: disable=raise-missing-from

    def __setitem__(self, key, value):
        # get mapping
        if isinstance(key, list):
            parent = key[:-1]
            key = key[-1]
            branch = self
            for p in parent:
                # overwrite value of key, if it is either not in the branch or it is not a mapping
                if not (p in branch and isinstance(branch[p], Mapping)):
                    branch[p] = Config()
                branch = branch[p]
            mapping = branch
        else:
            mapping = self._mapping

        # set value to mapping
        if isinstance(value, dict):
            mapping[key] = Config(value)
        else:
            mapping[key] = value

    def __setattr__(self, key, value):
        self[key] = value

    def __delitem__(self, key):
        del self._mapping[key]

    def __copy__(self):
        new = type(self)(self._mapping)
        return new

    def __iter__(self):
        return iter(self._mapping)

    def __len__(self):
        return len(self._mapping)

    def __repr__(self):
        return f"{type(self).__name__}({repr(self._mapping)})"


class ConfigValidator(Validator):

    class FlatErrorHandler(BasicErrorHandler):

        def __call__(self, errors: list[ValidationError]) -> list[dict[str, str | int | list[str]]]:
            return self._format_errors(errors)

        def _format_errors(self, errors: list[ValidationError]) -> list[dict[str, str | int | list[str]]]:
            formatted_errors = []
            for error in errors:
                if error.is_logic_error:
                    for definition_errors in error.definitions_errors.values():
                        formatted_errors.extend(self._format_errors(definition_errors))
                elif error.is_group_error:
                    formatted_errors.extend(self._format_errors(error.child_errors))
                elif error.code in self.messages:
                    formatted_errors.append(self._format_error(error))
            return formatted_errors

        def _format_error(self, error: ValidationError) -> dict[str, str | int | list[str]]:
            formatted_error = {
                "path": list(error.document_path),
                "code": error.code,
                "msg": self._format_message(error.field, error),
            }
            return formatted_error

    def __init__(self, *args: Any, **kwargs: Any):
        # extra types
        self.types_mapping['path'] = TypeDefinition('path', (Path,), ())

        super().__init__(*args, **kwargs)
        self.ignore_defaults = kwargs.get("ignore_defaults", False)
        self.purge_unknown = kwargs.get("purge_unknown", True)
        self.auto_coerce = kwargs.get("auto_coerce", True)
        self.error_handler = self.FlatErrorHandler()

    @staticmethod
    def _normalize_purge_unknown(mapping, schema):
        """{'type': 'boolean'}"""
        for field, value in list(mapping.items()):
            if field not in schema or value is None:
                mapping.pop(field)
        return mapping

    def _normalize_coerce(self, mapping, schema):
        """\
        {'oneof': [
            {'type': 'callable'},
            {'type': 'list',
             'schema': {'oneof': [{'type': 'callable'},
                                  {'type': 'string'}]}},
            {'type': 'string'}
        ]}
        """
        if self.auto_coerce:
            for field, value in mapping.items():
                if field in schema \
                    and "coerce" not in schema[field] \
                    and "type" in schema[field] \
                    and schema[field]["type"] != "string":
                    if not isinstance(value, str):
                        continue
                    value = value.strip()
                    type_ = schema[field]["type"]

                    if type_ == "boolean":
                        schema[field]["coerce"] = "boolean"
                    elif type_ == "float":
                        schema[field]["coerce"] = "float"
                    elif type_ == "integer":
                        schema[field]["coerce"] = "integer"
                    elif type_ == "list":
                        schema[field]["coerce"] = "semicolon_list"
                    elif type_ == "set":
                        schema[field]["coerce"] = "semicolon_set"
                    elif type_ == "datetime":
                        schema[field]["coerce"] = "datetime"
                    elif type_ == "path":
                        schema[field]["coerce"] = "path"

        super()._normalize_coerce(mapping, schema)

    def _normalize_default(self, mapping: Mapping, schema: Mapping, field: str) -> None:
        """ {'nullable': True} """
        if self.ignore_defaults:
            return
        if schema[field]['default'] is missing:
            self._error(field, REQUIRED_FIELD)
        else:
            mapping[field] = schema[field]['default']

    def _normalize_coerce_strip_str(self, value: Any) -> str:
        """Strip whitespaces of a string."""
        if isinstance(value, str):
            return value.strip()
        # leave other types untouched, so type validation will detect wrong types
        return value

    def _normalize_coerce_boolean(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return bool(str_to_bool(value))

    def _normalize_coerce_float(self, value: Any) -> float:
        if isinstance(value, float):
            return value
        return float(value)

    def _normalize_coerce_integer(self, value: Any) -> int:
        if isinstance(value, int):
            return value
        return int(value)

    def _normalize_coerce_semicolon_list(self, value: list[str] | set[str] | str) -> list:
        """Coerce a semicolon (';') delimited string into a proper list."""
        if isinstance(value, set):
            return list(value)
        if isinstance(value, list):
            return value
        return list(map(lambda vi: vi.strip(), value.split(';')))

    def _normalize_coerce_semicolon_set(self, value: list[str] | set[str] | str) -> set:
        """Coerce a semicolon (';') delimited string into a proper set."""
        if isinstance(value, set):
            return value
        if isinstance(value, list):
            return set(value)
        return set(map(lambda vi: vi.strip(), value.split(';')))

    def _normalize_coerce_datetime(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)

    def _normalize_coerce_path(self, value: Any) -> Path:
        if isinstance(value, Path):
            return value
        return Path(value)

    def _check_with_file_exists(self, field, value):
        """Check if a path exists and is a file."""
        if not value:
            return
        path = Path(value).resolve(strict=False)
        if not path.exists():
            self._error(field, f'File does not exist: {value}')
            return
        if not path.is_file():
            self._error(field, f'Path is not a file: {value}')

    def _check_with_dir_exists(self, field, value):
        """Check if a path exists and is a directory."""
        if not value:
            return
        path = Path(value).resolve(strict=False)
        if not path.exists():
            self._error(field, f'Directory does not exist: {value}')
            return
        if not path.is_dir():
            self._error(field, f'Path is not a directory: {value}')


class ConfigLoader:
    """ConfigLoader is an interface used to load a configuration from a source."""

    def load(self) -> Config:
        """Load a configuration from a source and normalize/validate it.

        Raises:
            ConfigException: If the loader was unable to load or
                normalize/validate the configuration.

        Returns:
            Config: Loaded and validated configuration.
        """
        raise NotOverriddenError()


class CliConfigLoader(ConfigLoader):
    """Configuration loader that loads a single YAML file.

    Args:
        schema (Mapping): Schema used for normalization/validation.
        config (Mapping): Configuration that need to be normalized and validated.
    """

    def __init__(self, schema: Mapping, config: Mapping | None) -> None:
        self._schema = schema
        self._config = {} if config is None else config

    def load(self) -> Config:
        validated, reasons = validate(self._config, self._schema, middle_stage=True)
        if reasons:
            raise ConfigError(f"Invalid option '{reasons[0]}'", reasons)
        return Config(validated)


class YamlFileConfigLoader(ConfigLoader):
    """Configuration loader that loads a single YAML file.

    Args:
        schema (Mapping): Schema used for normalization/validation.
        path (str or Path): Path to YAML file to be loaded.
    """

    def __init__(self, schema: Mapping, path: str | Path | None) -> None:
        self._schema = schema
        self._path = path if isinstance(path, Path) else Path(path) if path is not None else None

    def load(self) -> Config:
        if not self._path:
            return Config()
        try:
            # get YAML file content
            with self._path.open("r") as f:
                raw = yaml.safe_load(f) or {}
        except OSError as err:
            raise ConfigError(f"Failed to load YAML config: {err}", reasons=[str(err)]) from err

        # normalize and validate the yaml content
        validated, reasons = validate(raw, self._schema, middle_stage=True)
        if reasons:
            raise ConfigError(
                "There is one or more errors in the configuration file '{}':\n    {}".format(
                    self._path, "\n    ".join(reasons)),
                reasons,
            )
        return Config(validated)


class KrawlerConfigLoader(ConfigLoader):
    """Merge multiple ConfigLoaders and apply app specific transformation to the
    config.

    Args:
        *loaders (ConfigLoader): Loaders to be merged into one.
    """

    def __init__(self, schema: Mapping, *loaders: ConfigLoader) -> None:
        self._schema = schema
        self._loaders = loaders

    def load(self) -> Config:
        # load the configs using the specified loaders
        configs = [ldrs.load() for ldrs in self._loaders]

        # merge the configs
        merged: Config = Config()
        for key_path, _ in iterate_schema(self._schema):
            for config in configs:
                value = config.get([key_path], missing)
                if value != missing:
                    merged[key_path] = value

        # add defaults to fetchers (before validation)
        fetchers_config = merged.get("fetchers", {})
        fetchers_defaults = fetchers_config.get("defaults", {})
        for name in self._schema["fetchers"]["schema"]:
            if name != "defaults":
                for option, default_value in fetchers_defaults.items():
                    if name not in fetchers_config:
                        fetchers_config[name] = {}
                    if fetchers_config[name].get(option, missing) == missing:
                        fetchers_config[name][option] = default_value

        # normalize and validate the merged configs
        validated, reasons = validate(merged, self._schema)
        if reasons:
            raise ConfigError(
                "There is one or more errors in the configuration:\n    {}".format("\n    ".join(reasons)),
                reasons,
            )

        # add user_agent to each fetcher and repository config (after validation)
        fetchers_config = validated.fetchers
        for config_set in [validated.fetchers, validated.repositories]:
            for name in config_set:
                if name != "defaults":
                    config_set[name]["user_agent"] = validated.user_agent

        return Config(validated)
