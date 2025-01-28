# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import re
from dataclasses import dataclass

from krawl.dict_utils import DictUtils
from krawl.errors import ParserError

_re_cube = re.compile(
    r"cube\(size=\[(?P<width>[0-9]*(\.[0-9]*)?),(?P<height>[0-9]*(\.[0-9]*)?),(?P<depth>[0-9]*(\.[0-9]*)?)\]\)")
_re_cylinder = re.compile(r"cylinder\(h=(?P<height>[0-9]*(\.[0-9]*)?),r=(?P<radius>[0-9]*(\.[0-9]*)?)\)")


@dataclass(slots=True)
# DEPRECATED See OuterDimensions below
class OuterDimensionsOpenScad:
    """OuterDimensions data model, using the deprecated OpenSCAD model."""

    openscad: str  # example: "cube(size = [400,350,150])"
    unit: str  # example: "mm"

    @classmethod
    def from_dict(cls, data: dict) -> OuterDimensionsOpenScad:
        if data is None:
            raise ParserError(f"No data supplied to be parsed into {cls}")
        openscad = DictUtils.to_string(data.get("openSCAD", None))
        if not openscad:
            openscad = DictUtils.to_string(data.get("openscad", None))
        unit = DictUtils.to_string(data.get("unit", None))
        if not openscad or not unit:
            raise ParserError(f"Not all required fields for {cls} are present: {data}")
        outer_dimensions = cls(
            openscad=openscad,
            unit=unit,
        )
        return outer_dimensions


@dataclass(slots=True)
class OuterDimensions:
    """OuterDimensions data model.
    All dimensions are measured in [mm] (millimeter)."""

    width: float
    height: float
    depth: float

    @classmethod
    def from_dict(cls, data: dict) -> OuterDimensions:
        if data is None:
            return None
        width = DictUtils.to_float(data.get("width", None))
        height = DictUtils.to_float(data.get("height", None))
        depth = DictUtils.to_float(data.get("depth", None))
        if not width or not height or not depth:
            raise ParserError(f"Not all required fields for {cls} are present: {data}")
        outer_dimensions = cls(
            width=width,
            height=height,
            depth=depth,
        )
        return outer_dimensions

    @classmethod
    def from_openscad(cls, old: OuterDimensionsOpenScad) -> OuterDimensions:
        shape = old.openscad.replace(" ", "").replace("\t", "")

        width: float
        height: float
        depth: float
        match_res = _re_cube.match(shape)
        if match_res:
            width = float(match_res.group("width"))
            height = float(match_res.group("height"))
            depth = float(match_res.group("depth"))
        else:
            match_res = _re_cylinder.match(shape)
            if match_res:
                height = float(match_res.group("height"))
                radius = float(match_res.group("radius"))
                width = radius
                depth = radius
            else:
                raise ParserError(f"Unknown OpenSCAD shape '{old.openscad}';"
                                  " We currently only support single cubes,"
                                  " so a valid example would be 'cube(size=[400,350,150])'.")

        multiplier: int
        match old.unit.lower():
            case "mm" | "millimeter":
                multiplier = 1
            case "cm" | "centimeter":
                multiplier = 10
            case "m" | "meter":
                multiplier = 1000
            case _:
                raise ParserError(f"Unknown OpenSCAD unit: {old.unit}")

        return cls(
            width=width * multiplier,
            height=height * multiplier,
            depth=depth * multiplier,
        )
