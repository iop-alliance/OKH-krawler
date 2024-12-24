from __future__ import annotations

from dataclasses import dataclass, field

# from krawl.dict_utils import DictUtils
from krawl.model.file import File
# from krawl.model.licenses import get_spdx_by_id_or_name as get_license
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

    # @classmethod
    # def from_dict(cls, data: dict) -> Part:
    #     if data is None:
    #         return None
    #     part = cls()
    #     part.name = data.get("name", None)
    #     part.name_clean = data.get("name_clean", None)
    #     part.image = File.from_dict(data.get("image"))
    #     part.source = File.from_dict(data.get("source"))
    #     part.export = [File.from_dict(e) for e in data.get("export")]
    #     part.auxiliary = [File.from_dict(e) for e in data.get("auxiliary")]
    #     part.documentation_language = data.get("documentation-language", None)
    #     part.material = data.get("material", None)
    #     part.manufacturing_process = data.get("manufacturing-process", None)
    #     part.mass = DictUtils.to_float(data.get("mass"))
    #     outer_dimensions_raw = data.get("outer-dimensions")
    #     part.outer_dimensions = OuterDimensions.from_dict(outer_dimensions_raw)
    #     part.tsdc = data.get("tsdc", None)
    #     part.license = get_license(data.get("license", None))
    #     part.licensor = data.get("licensor", None)
    #     return part

    # def as_dict(self) -> dict:
    #     return {
    #         "name": self.name,
    #         "name_clean": self.name_clean,
    #         "image": self.image.as_dict() if self.image is not None else None,
    #         "source": self.source.as_dict() if self.source is not None else None,
    #         "export": [e.as_dict() for e in self.export if e is not None],
    #         "auxiliary": [e.as_dict() for e in self.auxiliary if e is not None],
    #         "documentation-language": self.documentation_language,
    #         "material": self.material,
    #         "manufacturing-process": self.manufacturing_process,
    #         "mass": self.mass,
    #         "outer-dimensions": self.outer_dimensions.as_dict() if self.outer_dimensions is not None else None,
    #         "tsdc": self.tsdc,
    #         "license": str(self.license),
    #         "licensor": self.licensor,
    #     }
    #     # return asdict(self)
