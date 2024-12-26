from __future__ import annotations

from dataclasses import dataclass

from krawl.model.file import File


@dataclass(slots=True)
class Software:
    """Software data model."""

    installation_guide: File = None
    documentation_language: str = None
    license: str = None
    licensor: str = None
    release: str | None = None
