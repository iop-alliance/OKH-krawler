import json

import toml
import yaml

from krawl.exceptions import NotAManifest


def parse_manifest(content: bytes, extension: str) -> dict:
    if is_binary(content):
        raise NotAManifest("File appears to be a binary ({download_url})")

    parsed = None
    if extension in [".yaml", ".yml"]:
        try:
            parsed = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise NotAManifest("failed to parse manifest content") from e
    elif extension == ".toml":
        try:
            parsed = toml.loads(content.decode('utf-8'))
        except toml.TomlDecodeError as e:
            raise NotAManifest("failed to parse manifest content") from e
    elif extension == ".json":
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            raise NotAManifest("failed to parse manifest content") from e

    if not parsed:
        raise NotAManifest("file is empty")

    return parsed


def is_binary(content: bytes) -> bool:
    """Return true if the given content is binary.

    Args:
        content (bytes): Content to be checked.
    """
    return b"\0" in content
