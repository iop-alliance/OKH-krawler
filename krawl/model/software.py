from __future__ import annotations

from dataclasses import dataclass

from krawl.model.file import File

# from krawl.model.licenses import get_spdx_by_id_or_name as get_license


@dataclass(slots=True)
class Software:
    """Software data model."""

    release: str = None
    installation_guide: File = None
    documentation_language: str = None
    license: str = None
    licensor: str = None

    # @classmethod
    # def from_dict(cls, data: dict) -> Software:
    #     if data is None:
    #         return None
    #     software = cls()
    #     software.release = data.get("release", None)
    #     software.installation_guide = File.from_dict(data.get("installation-guide"))
    #     software.documentation_language = data.get("documentation-language", None)
    #     software.license = get_license(data.get("license", None))
    #     software.licensor = data.get("licensor", None)
    #     return software

    # def as_dict(self) -> dict:
    #     return asdict(self)
