# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass, field

from krawl.model.file import File, Image
from krawl.model.outer_dimensions import OuterDimensions


@dataclass(slots=True)
class Part:  # pylint: disable=too-many-instance-attributes
    """Part data model."""

    name_clean: str
    name: str | None = None
    image: list[Image] = field(default_factory=list)
    source: list[File] = field(default_factory=list)
    export: list[File] = field(default_factory=list)
    auxiliary: list[File] = field(default_factory=list)
    # NOTE We don't want these here, as we want to promote file-level licensing information to be handled exclusively with REUSE/SPDX
    # license: str = None
    # licensor: str = None
    # documentation_language: str = None
    material: str | None = None
    manufacturing_instructions: list[File] = field(default_factory=list)
    # manufacturing_process: str | None = None
    mass: float | None = None
    outer_dimensions: OuterDimensions | None = None
    tsdc: str | None = None
