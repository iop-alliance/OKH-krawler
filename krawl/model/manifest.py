from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


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

    def alt_exts(self) -> list[str]:
        if self == ManifestFormat.YAML:
            return ["yaml"]
        return []


@dataclass(slots=True, frozen=True)
class Manifest:
    """The content and basic meta info of an OKH manifest file."""

    content: str | bytes = None
    format: ManifestFormat = None

    def is_valid(self) -> bool:
        return self.content and self.format
