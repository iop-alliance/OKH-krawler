# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum

import tomli
import yaml

from krawl.fetcher.util import recuperate_invalid_yaml_manifest
from krawl.recursive_type import RecDict


class ManifestFormat(StrEnum):
    """Valid file formats for an OKH manifest file."""
    JSON = "json"
    JSON_LD = "jsonld"
    TOML = "toml"
    TURTLE = "ttl"
    YAML = "yml"

    @classmethod
    def from_ext(cls, ext: str) -> ManifestFormat:
        ext_lower = ext.lower()
        try:
            return cls(ext_lower)
        except ValueError:
            for format in cls:
                for alt_ext in format.alt_exts():
                    if alt_ext == ext_lower:
                        return format
        raise ValueError(f"Unknown/Invalid manifest file extension '{ext}'")

    def alt_exts(self) -> list[str]:
        if self == ManifestFormat.YAML:
            return ["yaml"]
        return []

    def is_rdf(self) -> bool:
        match self:
            case ManifestFormat.TURTLE | ManifestFormat.JSON_LD:
                return True
            case ManifestFormat.JSON | ManifestFormat.TOML | ManifestFormat.YAML:
                return False
            case _:
                raise NotImplementedError


@dataclass(slots=True, frozen=True)
class Manifest:
    """The content and basic meta info of an OKH manifest file."""

    content: str | bytes | RecDict
    format: ManifestFormat

    def is_valid(self) -> bool:
        return bool(self.content) and bool(self.format)

    def as_dict(self) -> RecDict:
        if self.format.is_rdf():
            raise ValueError(f"Can't convert format '{self.format}' to dict; it is already RDF.")
        if isinstance(self.content, dict):
            return self.content
        content_bytes_orig = self.content.encode('utf-8') if isinstance(self.content, str) else self.content
        deserialized: RecDict
        try:
            match self.format:
                case ManifestFormat.JSON:
                    deserialized = json.loads(content_bytes_orig)
                case ManifestFormat.TOML:
                    deserialized = tomli.loads(content_bytes_orig.decode('utf-8'))
                case ManifestFormat.YAML:
                    content_bytes_valid = recuperate_invalid_yaml_manifest(content_bytes_orig)
                    deserialized = yaml.safe_load(content_bytes_valid)
                case _:
                    raise NotImplementedError
        except Exception as err:
            raise ValueError(f"Failed to convert manifest content to dict: {err}") from err
        return deserialized
