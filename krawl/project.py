from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path

from krawl.licenses import License, get_by_id_or_name
from krawl.platform_url import PlatformURL

class UploadMethods(Enum):
    AUTO = "auto" # crawled through the project hosting platforms API
    MANIFEST = "manifest" # via okh.(toml|yaml|...) manifest file (and API?)
    MANIFEST_SCRIPT = "manifest-script" # via a script that creates manifest files
    MANUAL = "manual" # TODO Document

    def __str__(self):
        return self.value


class ProjectID:
    """ProjectID serves as an identifier for projects, that can be used by the
    appropriate fetcher to fetch the projects metadata.

    Args:
        platform (str): The domain of the platform.
        owner (str): User or group that owns the project.
        repo (str): Name of the project repository.
        path (str): Canoncial path of the manifest file inside the repository, if any.
    """

    __slots__ = ["platform", "owner", "repo", "path"]

    def __init__(self, platform: str, owner: str, repo: str, path: str = None) -> None:
        self.platform: str = platform
        self.owner: str = owner
        self.repo: str = repo
        self.path: str = path

    def __str__(self) -> str:
        if self.path:
            return f"{self.platform}/{self.owner}/{self.repo}/{self.path}"
        return f"{self.platform}/{self.owner}/{self.repo}"

    @classmethod
    def from_url(cls, url: str) -> ProjectID:
        pu = PlatformURL.from_url(url)

        if pu.platform == "oshwa.org":
            return cls(platform=pu.platform, repo=pu.repo, path=pu.path, owner='none')

        if not pu.owner:
            raise ValueError(f"could not extract owner from URL '{url}'")
        if not pu.repo:
            raise ValueError(f"could not extract repo from URL '{url}'")

        if pu.path:
            return cls(pu.platform, pu.owner, pu.repo, str(pu.path))

        return cls(pu.platform, pu.owner, pu.repo)


class Project:
    """Project data model based on
    https://github.com/OPEN-NEXT/OKH-LOSH/blob/master/sample_data/okh-TEMPLATE.toml.
    """

    __slots__ = [
        "meta", "okhv", "name", "repo", "version", "release", "license", "licensor", "organization", "readme",
        "contribution_guide", "image", "documentation_language", "technology_readiness_level",
        "documentation_readiness_level", "attestation", "publication", "function", "standard_compliance",
        "cpc_patent_class", "tsdc", "bom", "manufacturing_instructions", "user_manual", "part", "software",
        "specific_api_data", "source", "export", "upload_method"
    ]

    def __init__(self) -> None:
        # for internal use
        self.meta = Meta()

        # from the specification
        self.okhv: str = "OKH-LOSHv1.0"
        self.name: str = None
        self.repo: str = None
        self.version: str = None
        self.release: str = None
        self.license: License = None
        self.licensor: str = None
        self.organization: str = None
        self.readme: File = None
        self.contribution_guide: File = None
        self.image: File = None
        self.documentation_language: str = None
        self.technology_readiness_level: str = None
        self.documentation_readiness_level: str = None
        self.attestation: str = None
        self.publication: str = None
        self.function: str = None
        self.standard_compliance: str = None
        self.cpc_patent_class: str = None
        self.tsdc: str = None
        self.bom: File = None
        self.manufacturing_instructions: File = None
        self.user_manual: File = None
        self.part: list[Part] = []
        self.software: list[Software] = []
        self.upload_method = None
        self.source = []
        self.export = []

        self.specific_api_data = dict()

    @classmethod
    def from_dict(cls, data: dict) -> Project | None:
        if data is None:
            return None
        project = cls()
        project.meta = Meta.from_dict(data.get("__meta", {}))
        project.okhv = data.get("okhv", None)
        project.name = data.get("name", None)
        project.repo = data.get("repo", None)
        project.version = data.get("version", None)
        project.release = data.get("release", None)
        project.license = get_by_id_or_name(data.get("license", None))
        project.licensor = data.get("licensor", None)
        project.organization = data.get("organization", None)
        project.readme = File.from_dict(data.get("readme"))
        project.contribution_guide = File.from_dict(data.get("contribution-guide"))
        project.image = File.from_dict(data.get("image"))
        project.documentation_language = data.get("documentation-language", None)
        project.technology_readiness_level = data.get("technology-readiness-level", None)
        project.documentation_readiness_level = data.get("documentation-readiness-level", None)
        project.attestation = data.get("attestation", None)
        project.publication = data.get("publication", None)
        project.function = data.get("function", None)
        project.standard_compliance = data.get("standard-compliance", None)
        project.cpc_patent_class = data.get("cpc-patent-class", None)
        project.tsdc = data.get("tsdc", None)
        project.bom = File.from_dict(data.get("bom"))
        project.manufacturing_instructions = File.from_dict(data.get("manufacturing-instructions"))
        project.user_manual = File.from_dict(data.get("user-manual"))
        project.part = [Part.from_dict(p) for p in data.get("part", [])]
        project.software = [Software.from_dict(s) for s in data.get("software", [])]
        project.specific_api_data = data.get('specific-api-data')
        project.upload_method = data.get('upload-method')
        return project

    def as_dict(self) -> dict:
        return {
            "__meta": self.meta.as_dict(),
            "okhv": self.okhv,
            "name": self.name,
            "repo": self.repo,
            "version": self.version,
            "release": self.release,
            "license": str(self.license),
            "licensor": self.licensor,
            "organization": self.organization,
            "readme": self.readme.as_dict() if self.readme is not None else None,
            "contribution-guide": self.contribution_guide.as_dict() if self.contribution_guide is not None else None,
            "image": self.image.as_dict() if self.image is not None else None,
            "documentation-language": self.documentation_language,
            "technology-readiness-level": self.technology_readiness_level,
            "documentation-readiness-level": self.documentation_readiness_level,
            "attestation": self.attestation,
            "publication": self.publication,
            "function": self.function,
            "standard-compliance": self.standard_compliance,
            "cpc-patent-class": self.cpc_patent_class,
            "tsdc": self.tsdc,
            "bom": self.bom.as_dict() if self.bom is not None else None,
            "manufacturing-instructions": self.manufacturing_instructions.as_dict()
                                          if self.manufacturing_instructions is not None else None,
            "user-manual": self.user_manual.as_dict() if self.user_manual is not None else None,
            "part": [p.as_dict() for p in self.part],
            "software": [s.as_dict() for s in self.software],
            "specific-api-data": self.specific_api_data,
            "upload-method": self.upload_method.value
        }

    @property
    def id(self) -> ProjectID:
        """Generates an ID in form of 'platform/owner/name'"""
        return ProjectID(self.meta.source, self.meta.owner, self.meta.repo, self.meta.path)


class Meta:
    """Metadata for internal use."""

    __slots__ = [
        "source", "owner", "repo", "path", "branch", "created_at", "last_visited", "last_changed", "history", "score"
    ]

    def __init__(self) -> None:
        self.source: str = None  # where the project/manifest was found
        self.owner: str = None  # owner of the repository
        self.repo: str = None  # domain name of the repository
        self.path: str = None  # path of project/manifest inside the repository
        self.branch: str = None  # branch, in which the project/manifest was found
        self.created_at: datetime = None
        self.last_visited: datetime = None
        self.last_changed: datetime = None
        self.history = None
        # internally calculated score for project importance to decide re-visit schedule
        self.score = None

    @classmethod
    def from_dict(cls, data: dict) -> Meta:
        if data is None:
            return None
        meta = cls()
        meta.source = data.get("source", None)
        meta.owner = data.get("owner", None)
        meta.repo = data.get("repo", None)
        meta.path = data.get("path", None)
        meta.branch = data.get("branch", None)
        meta.created_at = _parse_date(data.get("created-at"))
        meta.last_visited = _parse_date(data.get("last-visited"))
        meta.last_changed = _parse_date(data.get("last-changed"))
        meta.history = data.get("history", None)
        meta.score = data.get("score", None)
        return meta

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "owner": self.owner,
            "repo": self.repo,
            "path": self.path,
            "branch": self.branch,
            "created-at": self.created_at.isoformat() if self.created_at is not None else None,
            "last-visited": self.last_visited.isoformat() if self.last_visited is not None else None,
            "last-changed": self.last_changed.isoformat() if self.last_changed is not None else None,
            "history": self.history,
            "score": self.score,
        }


class Part:
    """Part data model."""

    __slots__ = [
        "name", "image", "source", "export", "auxiliary", "documentation_language", "material", "manufacturing_process",
        "mass", "outer_dimensions", "tsdc", "license", "licensor"
    ]

    def __init__(self) -> None:
        self.name: str = None
        self.image: File = None
        self.source: File = None
        self.export: list[File] = []
        self.auxiliary: list[File] = []
        self.license: License = None
        self.licensor: str = None
        self.documentation_language: str = None
        self.material: str = None
        self.manufacturing_process: str = None
        self.mass: Mass = None
        self.outer_dimensions: OuterDimensions = None
        self.tsdc: str = None

    @classmethod
    def from_dict(cls, data: dict) -> Part:
        if data is None:
            return None
        part = cls()
        part.name = data.get("name", None)
        part.image = File.from_dict(data.get("image"))
        part.source = File.from_dict(data.get("source"))
        part.export = [File.from_dict(e) for e in data.get("export")]
        part.auxiliary = [File.from_dict(e) for e in data.get("auxiliary")]
        part.documentation_language = data.get("documentation-language", None)
        part.material = data.get("material", None)
        part.manufacturing_process = data.get("manufacturing-process", None)
        part.mass = Mass.from_dict(data.get("mass"))
        part.outer_dimensions = OuterDimensions.from_dict(data.get("outer-dimensions"))
        part.tsdc = data.get("tsdc", None)
        part.license = get_by_id_or_name(data.get("license", None))
        part.licensor = data.get("licensor", None)
        return part

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "image": self.image.as_dict() if self.image is not None else None,
            "source": self.source.as_dict() if self.source is not None else None,
            "export": [e.as_dict() for e in self.export if e is not None],
            "auxiliary": [e.as_dict() for e in self.auxiliary if e is not None],
            "documentation-language": self.documentation_language,
            "material": self.material,
            "manufacturing-process": self.manufacturing_process,
            "mass": self.mass.as_dict() if self.mass is not None else None,
            "outer-dimensions": self.outer_dimensions.as_dict() if self.outer_dimensions is not None else None,
            "tsdc": self.tsdc,
            "license": str(self.license),
            "licensor": self.licensor,
        }


class Mass:
    """Mass data model."""

    __slots__ = ["value", "unit"]

    def __init__(self) -> None:
        self.value: float = None
        self.unit: str = None

    @classmethod
    def from_dict(cls, data: dict) -> Mass:
        if data is None:
            return None
        mass = cls()
        mass.value = data.get("value", None)
        mass.unit = data.get("unit", None)
        return mass

    def as_dict(self) -> dict:
        return {
            "value": self.value,
            "unit": self.unit,
        }


class OuterDimensions:
    """OuterDimensions data model."""

    __slots__ = ["openscad", "unit"]

    def __init__(self) -> None:
        self.openscad: str = None
        self.unit: str = None

    @classmethod
    def from_dict(cls, data: dict) -> OuterDimensions:
        if data is None:
            return None
        outer_dimensions = cls()
        outer_dimensions.openscad = data.get("openscad", None)
        outer_dimensions.unit = data.get("unit", None)
        return outer_dimensions

    def as_dict(self) -> dict:
        return {
            "openscad": self.openscad,
            "unit": self.unit,
        }


class Software:
    """Software data model."""

    __slots__ = ["release", "installation_guide", "documentation_language", "license", "licensor"]

    def __init__(self) -> None:
        self.release: str = None
        self.installation_guide: File = None
        self.documentation_language: str = None
        self.license: License = None
        self.licensor: str = None

    @classmethod
    def from_dict(cls, data: dict) -> Software:
        if data is None:
            return None
        software = cls()
        software.release = data.get("realease", None)
        software.installation_guide = File.from_dict(data.get("installation-guide"))
        software.documentation_language = data.get("documentation-language", None)
        software.license = get_by_id_or_name(data.get("license", None))
        software.licensor = data.get("licensor", None)
        return software

    def as_dict(self) -> dict:
        return {
            "release": self.release,
            "installation-guide": self.installation_guide.as_dict() if self.installation_guide is not None else None,
            "documentation-language": self.documentation_language,
            "license": str(self.license),
            "licensor": self.licensor,
        }


class File:
    """File data model."""

    __slots__ = [
        "name", "path", "mime_type", "url", "perma_url", "created_at", "last_visited", "last_changed", "license",
        "licensor"
    ]

    def __init__(self) -> None:
        self.name: str = None
        self.path: Path = None
        self.mime_type: str = None
        self.url: str = None
        self.perma_url: str = None  # perma URL is bound to a specific commit
        self.created_at: datetime = None
        self.last_visited: datetime = None
        self.last_changed: datetime = None
        self.license: License = None
        self.licensor: str = None

    @property
    def extension(self):
        return self.path.suffix[1:].lower() if self.path else ""

    @classmethod
    def from_dict(cls, data: dict) -> Part:
        if data is None:
            return None
        file = cls()
        file.name = data.get("name", None)
        file.path = Path(data["path"]) if data.get("path") is not None else None
        file.mime_type = data.get("mime-type", None)
        file.url = data.get("url", None)
        file.perma_url = data.get("perma-url", None)
        file.created_at = _parse_date(data.get("created-at"))
        file.last_visited = _parse_date(data.get("last-visited"))
        file.last_changed = _parse_date(data.get("last-changed"))
        file.license = get_by_id_or_name(data.get("license", None))
        file.licensor = data.get("licensor", None)
        return file

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "path": str(self.path),
            "mime-type": self.mime_type,
            "url": self.url,
            "perma-url": self.perma_url,
            "created-at": self.created_at.isoformat() if self.created_at is not None else None,
            "last-visited": self.last_visited.isoformat() if self.last_visited is not None else None,
            "last-changed": self.last_changed.isoformat() if self.last_changed is not None else None,
            "license": str(self.license),
            "licensor": self.licensor,
        }


class User:
    """User data model."""

    __slots__ = ["name", "email", "username", "language"]

    def __init__(self) -> None:
        self.name: str = None
        self.email: str = None
        self.username: str = None
        self.language: str = None


def _parse_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise ValueError("cannot parse date")
