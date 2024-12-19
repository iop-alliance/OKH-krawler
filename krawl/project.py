from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from krawl import dict_utils
from krawl.errors import ParserError
from krawl.licenses import License, get_by_id_or_name
from krawl.platform_url import PlatformURL


class UploadMethods(StrEnum):
    AUTO = "auto"  # crawled through the project hosting platforms API
    MANIFEST = "manifest"  # via okh.(toml|yaml|...) manifest file (and API?)
    MANIFEST_SCRIPT = "manifest-script"  # via a script that creates manifest files
    MANUAL = "manual"  # TODO Document


@dataclass(slots=True)
class ProjectID:
    """ProjectID serves as an identifier for projects, that can be used by the
    appropriate fetcher to fetch the projects metadata.

    Args:
        platform (str): The domain of the platform.
        owner (str): User or group that owns the project.
        repo (str): Name of the project repository.
        path (str): Canonical path of the manifest file inside the repository, if any.
    """

    platform: str
    owner: str
    repo: str
    path: str = None

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


@dataclass(slots=True)
class Project:  # pylint: disable=too-many-instance-attributes
    """Project data model based on
    https://github.com/iop-alliance/OpenKnowHow/blob/master/res/sample_data/okh-TEMPLATE.toml.
    """

    # for internal use
    meta: Meta = field(default_factory=Meta, init=False, repr=False)
    okhv: str = "OKH-LOSHv1.0"
    name: str = None
    repo: str = None
    version: str = None
    release: str = None
    license: License = None
    licensor: str = None
    organization: str = None
    readme: File = None
    contribution_guide: File = None
    image: File = None
    documentation_language: str = None
    technology_readiness_level: str = None
    documentation_readiness_level: str = None
    attestation: str = None
    publication: str = None
    function: str = None
    standard_compliance: str = None
    cpc_patent_class: str = None
    tsdc: str = None
    bom: File = None
    manufacturing_instructions: File = None
    user_manual: File = None
    part: list[Part] = []
    software: list[Software] = []
    upload_method = None
    source = []
    export = []
    specific_api_data = {}

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
        # return asdict(self)
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
            "upload-method": str(self.upload_method)
        }

    @property
    def id(self) -> ProjectID:
        """Generates an ID in form of 'platform/owner/repo/path'"""
        return ProjectID(self.meta.source, self.meta.owner, self.meta.repo, self.meta.path)


@dataclass(slots=True)
class Meta:  # pylint: disable=too-many-instance-attributes
    """Metadata for internal use."""

    source: str = None  # where the project/manifest was found
    owner: str = None  # owner of the repository
    repo: str = None  # domain name of the repository
    path: str = None  # path of project/manifest inside the repository
    branch: str = None  # branch, in which the project/manifest was found
    created_at: datetime = None
    last_visited: datetime = None
    last_changed: datetime = None
    history = None
    # # internally calculated score for project importance to decide re-visit schedule
    # score: Meta = field(default=None, init=False)

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
        # meta.score = data.get("score", None)
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
            # "score": self.score,
        }


@dataclass(slots=True)
class Part:  # pylint: disable=too-many-instance-attributes
    """Part data model."""

    name: str = None
    name_clean: str = None
    image: File = None
    source: File = None
    export: list[File] = []
    auxiliary: list[File] = []
    license: License = None
    licensor: str = None
    documentation_language: str = None
    material: str = None
    manufacturing_process: str = None
    mass: float = None
    outer_dimensions: OuterDimensions = None
    tsdc: str = None

    @classmethod
    def from_dict(cls, data: dict) -> Part:
        if data is None:
            return None
        part = cls()
        part.name = data.get("name", None)
        part.name_clean = data.get("name_clean", None)
        part.image = File.from_dict(data.get("image"))
        part.source = File.from_dict(data.get("source"))
        part.export = [File.from_dict(e) for e in data.get("export")]
        part.auxiliary = [File.from_dict(e) for e in data.get("auxiliary")]
        part.documentation_language = data.get("documentation-language", None)
        part.material = data.get("material", None)
        part.manufacturing_process = data.get("manufacturing-process", None)
        part.mass = dict_utils.to_float(data.get("mass"))
        outer_dimensions_raw = data.get("outer-dimensions")
        part.outer_dimensions = OuterDimensions.from_dict(outer_dimensions_raw)
        part.tsdc = data.get("tsdc", None)
        part.license = get_by_id_or_name(data.get("license", None))
        part.licensor = data.get("licensor", None)
        return part

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "name_clean": self.name_clean,
            "image": self.image.as_dict() if self.image is not None else None,
            "source": self.source.as_dict() if self.source is not None else None,
            "export": [e.as_dict() for e in self.export if e is not None],
            "auxiliary": [e.as_dict() for e in self.auxiliary if e is not None],
            "documentation-language": self.documentation_language,
            "material": self.material,
            "manufacturing-process": self.manufacturing_process,
            "mass": self.mass,
            "outer-dimensions": self.outer_dimensions.as_dict() if self.outer_dimensions is not None else None,
            "tsdc": self.tsdc,
            "license": str(self.license),
            "licensor": self.licensor,
        }
        # return asdict(self)


@dataclass(slots=True)
class Mass:
    """Mass data model."""

    value: float = None
    unit: str = None

    @classmethod
    def from_dict(cls, data: dict) -> Mass:
        if data is None:
            return None
        mass = cls()
        mass.value = data.get("value", None)
        mass.unit = data.get("unit", None)
        if not mass.is_valid():
            raise ParserError(f"Not all required fields for {cls} are present: {data}")
        return mass

    def as_dict(self) -> dict:
        return asdict(self)

    def is_valid(self) -> bool:
        return not (self.value is None or self.unit is None)


@dataclass(slots=True)
# DEPRECATED See OuterDimensions below
class OuterDimensionsOpenScad:
    """OuterDimensions data model, using the deprecated OpenSCAD model."""

    openscad: str = None
    unit: str = None

    @classmethod
    def from_dict(cls, data: dict) -> OuterDimensions:
        if data is None:
            return None
        outer_dimensions = cls()
        outer_dimensions.openscad = data.get("openscad", None)
        outer_dimensions.unit = data.get("unit", None)
        if not outer_dimensions.is_valid():
            raise ParserError(f"Not all required fields for {cls} are present: {data}")
        return outer_dimensions

    def as_dict(self) -> dict:
        return asdict(self)

    def is_valid(self) -> bool:
        return not (self.openscad is None or self.unit is None)


@dataclass(slots=True)
class OuterDimensions:
    """OuterDimensions data model.
    All dimensions are measured in [mm] (mili-meter)."""

    width: float = None
    height: float = None
    depth: float = None

    @classmethod
    def from_dict(cls, data: dict) -> OuterDimensions:
        if data is None:
            return None
        outer_dimensions = cls()
        outer_dimensions.width = dict_utils.to_float(data.get("width", None))
        outer_dimensions.height = dict_utils.to_float(data.get("height", None))
        outer_dimensions.depth = dict_utils.to_float(data.get("depth", None))
        if not outer_dimensions.is_valid():
            raise ParserError(f"Not all required fields for {cls} are present: {data}")
        return outer_dimensions

    @classmethod
    def from_openscad(cls, old: OuterDimensionsOpenScad) -> OuterDimensions:
        raise NotImplementedError()  # TODO

    def as_dict(self) -> dict:
        return asdict(self)

    def is_valid(self) -> bool:
        return not (self.width is None or self.height is None or self.depth is None)


@dataclass(slots=True)
class Software:
    """Software data model."""

    release: str = None
    installation_guide: File = None
    documentation_language: str = None
    license: License = None
    licensor: str = None

    @classmethod
    def from_dict(cls, data: dict) -> Software:
        if data is None:
            return None
        software = cls()
        software.release = data.get("release", None)
        software.installation_guide = File.from_dict(data.get("installation-guide"))
        software.documentation_language = data.get("documentation-language", None)
        software.license = get_by_id_or_name(data.get("license", None))
        software.licensor = data.get("licensor", None)
        return software

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class File:  # pylint: disable=too-many-instance-attributes
    """File data model."""

    name: str = None
    path: Path = None
    mime_type: str = None
    url: str = None
    frozen_url: str = None  # frozen URL is bound to a specific version of the file, e.g. a git commit
    created_at: datetime = None
    last_visited: datetime = None
    last_changed: datetime = None
    license: License = None
    licensor: str = None

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
        file.frozen_url = data.get("frozen-url", None)
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
            "frozen-url": self.frozen_url,
            "created-at": self.created_at.isoformat() if self.created_at is not None else None,
            "last-visited": self.last_visited.isoformat() if self.last_visited is not None else None,
            "last-changed": self.last_changed.isoformat() if self.last_changed is not None else None,
            "license": str(self.license),
            "licensor": self.licensor,
        }


@dataclass(slots=True)
class User:
    """User data model."""

    name: str = None
    email: str = None
    username: str = None
    language: str = None


def _parse_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise ValueError("cannot parse date")
