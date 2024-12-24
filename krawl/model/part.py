from __future__ import annotations

from dataclasses import dataclass, field

from krawl.model.file import File
from krawl.model.outer_dimensions import OuterDimensions


@dataclass(slots=True)
class Part:  # pylint: disable=too-many-instance-attributes
    """Part data model."""

    name: str = None
    name_clean: str = None
    image: File = None
    source: File = None
    export: list[File] = field(default_factory=list)
    auxiliary: list[File] = field(default_factory=list)
    license: str = None
    licensor: str = None
    documentation_language: str = None
    material: str = None
    manufacturing_process: str = None
    mass: float = None
    outer_dimensions: OuterDimensions = None
    tsdc: str = None
