from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path

import toml
import yaml

from krawl.exceptions import NotAManifest

_manifest_name_pattern = r"^okh([_\-\t ].+)*$"


def parse_manifest(content: bytes, path: Path) -> dict:
    name = path.stem.lower()
    suffix = path.suffix
    if not re.match(_manifest_name_pattern, name):
        raise NotAManifest("invalid file name")

    if is_binary(content):
        raise NotAManifest("File appears to be binary")

    parsed = None
    if suffix in [".yaml", ".yml"]:
        try:
            parsed = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise NotAManifest("failed to parse manifest content") from e
    elif suffix == ".toml":
        try:
            parsed = toml.loads(content.decode('utf-8'))
        except toml.TomlDecodeError as e:
            raise NotAManifest("failed to parse manifest content") from e
    elif suffix == ".json":
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            raise NotAManifest("failed to parse manifest content") from e

    if not parsed:
        raise NotAManifest("file is empty")
    if not isinstance(parsed, Mapping):
        raise NotAManifest("manifest has invalid content")

    return parsed


def is_binary(content: bytes) -> bool:
    """Return true if the given content is binary.

    Args:
        content (bytes): Content to be checked.
    """
    return b"\0" in content
