from __future__ import annotations

from dataclasses import dataclass, field

from krawl.model.data_set import DataSet
from krawl.model.file import File
from krawl.model.licenses import License
from krawl.model.licenses import get_by_id_or_name as get_license
from krawl.model.part import Part
from krawl.model.project_id import ProjectID
from krawl.model.software import Software
from krawl.model.sourcing_procedure import SourcingProcedure


@dataclass(slots=True)
class Project:  # pylint: disable=too-many-instance-attributes
    """Project data model based on
    https://github.com/iop-alliance/OpenKnowHow/blob/master/res/sample_data/okh-TEMPLATE.toml.
    """

    # for internal use
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
    image: list[File] = field(default_factory=list)
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
    part: list[Part] = field(default_factory=list)
    software: list[Software] = field(default_factory=list)
    sourcing_procedure: SourcingProcedure = None
    source: list[File] = field(default_factory=list)
    export: list[File] = field(default_factory=list)
    specific_api_data = {}
    # meta: DataSet = field(default_factory=DataSet, init=False, repr=False)

    # @classmethod
    # def from_dict(cls, data: dict) -> Project | None:
    #     if data is None:
    #         return None
    #     project = cls()
    #     project.meta = DataSet.from_dict(data.get("__meta", {}))
    #     project.okhv = data.get("okhv", None)
    #     project.name = data.get("name", None)
    #     project.repo = data.get("repo", None)
    #     project.version = data.get("version", None)
    #     project.release = data.get("release", None)
    #     project.license = get_by_id_or_name(data.get("license", None))
    #     project.licensor = data.get("licensor", None)
    #     project.organization = data.get("organization", None)
    #     project.readme = File.from_dict(data.get("readme"))
    #     project.contribution_guide = File.from_dict(data.get("contribution-guide"))
    #     project.image = File.from_dict(data.get("image"))
    #     project.documentation_language = data.get("documentation-language", None)
    #     project.technology_readiness_level = data.get("technology-readiness-level", None)
    #     project.documentation_readiness_level = data.get("documentation-readiness-level", None)
    #     project.attestation = data.get("attestation", None)
    #     project.publication = data.get("publication", None)
    #     project.function = data.get("function", None)
    #     project.standard_compliance = data.get("standard-compliance", None)
    #     project.cpc_patent_class = data.get("cpc-patent-class", None)
    #     project.tsdc = data.get("tsdc", None)
    #     project.bom = File.from_dict(data.get("bom"))
    #     project.manufacturing_instructions = File.from_dict(data.get("manufacturing-instructions"))
    #     project.user_manual = File.from_dict(data.get("user-manual"))
    #     project.part = [Part.from_dict(p) for p in data.get("part", [])]
    #     project.software = [Software.from_dict(s) for s in data.get("software", [])]
    #     project.specific_api_data = data.get('specific-api-data')
    #     project.sourcing_procedure = SourcingProcedure(data.get('data-sourcing-procedure'))
    #     return project

    # def as_dict(self) -> dict:
    #     # return asdict(self)
    #     return {
    #         "__meta": self.meta.as_dict(),
    #         "okhv": self.okhv,
    #         "name": self.name,
    #         "repo": self.repo,
    #         "version": self.version,
    #         "release": self.release,
    #         "license": str(self.license),
    #         "licensor": self.licensor,
    #         "organization": self.organization,
    #         "readme": self.readme.as_dict() if self.readme is not None else None,
    #         "contribution-guide": self.contribution_guide.as_dict() if self.contribution_guide is not None else None,
    #         "image": [s.as_dict() for s in self.image],
    #         "documentation-language": self.documentation_language,
    #         "technology-readiness-level": self.technology_readiness_level,
    #         "documentation-readiness-level": self.documentation_readiness_level,
    #         "attestation": self.attestation,
    #         "publication": self.publication,
    #         "function": self.function,
    #         "standard-compliance": self.standard_compliance,
    #         "cpc-patent-class": self.cpc_patent_class,
    #         "tsdc": self.tsdc,
    #         "bom": self.bom.as_dict() if self.bom is not None else None,
    #         "manufacturing-instructions": self.manufacturing_instructions.as_dict()
    #                                       if self.manufacturing_instructions is not None else None,
    #         "user-manual": self.user_manual.as_dict() if self.user_manual is not None else None,
    #         "part": [p.as_dict() for p in self.part],
    #         "software": [s.as_dict() for s in self.software],
    #         "source": [s.as_dict() for s in self.source],
    #         "data-sourcing-procedure": str(self.sourcing_procedure),
    #         "export": [s.as_dict() for s in self.export],
    #         "specific-api-data": self.specific_api_data,
    #     }

    @property
    def id(self) -> ProjectID:
        """Generates an ID in form of 'platform/owner/repo/path'"""
        # return ProjectID(self.meta.source, self.meta.owner, self.meta.repo, self.meta.path)
        return ProjectID.from_url(self.repo)
