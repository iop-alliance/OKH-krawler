from __future__ import annotations

from dataclasses import dataclass

# from krawl.errors import ParserError


@dataclass(slots=True)
class Mass:
    """Mass data model."""

    value: float = None
    unit: str = None

    # @classmethod
    # def from_dict(cls, data: dict) -> Mass:
    #     if data is None:
    #         return None
    #     mass = cls()
    #     mass.value = data.get("value", None)
    #     mass.unit = data.get("unit", None)
    #     if not mass.is_valid():
    #         raise ParserError(f"Not all required fields for {cls} are present: {data}")
    #     return mass

    # def as_dict(self) -> dict:
    #     return asdict(self)

    def is_valid(self) -> bool:
        return not (self.value is None or self.unit is None)
