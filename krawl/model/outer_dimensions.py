# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass

from krawl.dict_utils import DictUtils
from krawl.errors import ParserError


@dataclass(slots=True)
# DEPRECATED See OuterDimensions below
class OuterDimensionsOpenScad:
    """OuterDimensions data model, using the deprecated OpenSCAD model."""

    openscad: str = None  # example: "cube(size = [400,350,150])"
    unit: str = None  # example: "mm"

    @classmethod
    def from_dict(cls, data: dict) -> OuterDimensions:
        if data is None:
            return None
        outer_dimensions = cls()
        outer_dimensions.openscad = DictUtils.to_float(data.get("openscad", None))
        outer_dimensions.unit = DictUtils.to_float(data.get("unit", None))
        if not outer_dimensions.is_valid():
            raise ParserError(f"Not all required fields for {cls} are present: {data}")
        return outer_dimensions

    def is_valid(self) -> bool:
        return not (self.openscad is None or self.unit is None)


@dataclass(slots=True)
class OuterDimensions:
    """OuterDimensions data model.
    All dimensions are measured in [mm] (millimeter)."""

    width: float = None
    height: float = None
    depth: float = None

    @classmethod
    def from_dict(cls, data: dict) -> OuterDimensions:
        if data is None:
            return None
        outer_dimensions = cls()
        outer_dimensions.width = DictUtils.to_float(data.get("width", None))
        outer_dimensions.height = DictUtils.to_float(data.get("height", None))
        outer_dimensions.depth = DictUtils.to_float(data.get("depth", None))
        if not outer_dimensions.is_valid():
            raise ParserError(f"Not all required fields for {cls} are present: {data}")
        return outer_dimensions

    @classmethod
    def from_openscad(cls, old: OuterDimensionsOpenScad) -> OuterDimensions:
        shape = old.openscad.replace(" ", "").replace("\t", "")
        dims_bare_str = shape.removeprefix("cube(size=[").removesuffix("]")
        dims_str = dims_bare_str.split(",")
        if len(dims_str) != 3:
            raise ParserError(f"Unknown OpenSCAD shape: {old.openscad}")
        multiplier: int = None
        match old.unit:
            case "mm" | "millimeter":
                multiplier = 1
            case "cm" | "centimeter":
                multiplier = 10
            case "m" | "meter":
                multiplier = 1000
            case _:
                raise ParserError(f"Unknown OpenSCAD unit: {old.unit}")
        dims_bare = [float(dim) * multiplier for dim in dims_str]
        cls(
            width=dims_bare[0],
            height=dims_bare[1],
            depth=dims_bare[2],
        )

    def is_valid(self) -> bool:
        return (self.width and self.height and self.depth)
