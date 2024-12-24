from __future__ import annotations

from dataclasses import dataclass

# from krawl.dict_utils import DictUtils
# from krawl.errors import ParserError


@dataclass(slots=True)
# DEPRECATED See OuterDimensions below
class OuterDimensionsOpenScad:
    """OuterDimensions data model, using the deprecated OpenSCAD model."""

    openscad: str = None
    unit: str = None

    # @classmethod
    # def from_dict(cls, data: dict) -> OuterDimensions:
    #     if data is None:
    #         return None
    #     outer_dimensions = cls()
    #     outer_dimensions.openscad = data.get("openscad", None)
    #     outer_dimensions.unit = data.get("unit", None)
    #     if not outer_dimensions.is_valid():
    #         raise ParserError(f"Not all required fields for {cls} are present: {data}")
    #     return outer_dimensions

    # def as_dict(self) -> dict:
    #     return asdict(self)

    def is_valid(self) -> bool:
        return not (self.openscad is None or self.unit is None)


@dataclass(slots=True)
class OuterDimensions:
    """OuterDimensions data model.
    All dimensions are measured in [mm] (mili-meter)."""

    width: float = None
    height: float = None
    depth: float = None

    # @classmethod
    # def from_dict(cls, data: dict) -> OuterDimensions:
    #     if data is None:
    #         return None
    #     outer_dimensions = cls()
    #     outer_dimensions.width = DictUtils.to_float(data.get("width", None))
    #     outer_dimensions.height = DictUtils.to_float(data.get("height", None))
    #     outer_dimensions.depth = DictUtils.to_float(data.get("depth", None))
    #     if not outer_dimensions.is_valid():
    #         raise ParserError(f"Not all required fields for {cls} are present: {data}")
    #     return outer_dimensions

    @classmethod
    def from_openscad(cls, old: OuterDimensionsOpenScad) -> OuterDimensions:
        raise NotImplementedError()  # TODO

    # def as_dict(self) -> dict:
    #     return asdict(self)

    def is_valid(self) -> bool:
        return not (self.width is None or self.height is None or self.depth is None)
