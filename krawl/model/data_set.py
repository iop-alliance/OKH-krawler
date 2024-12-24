from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from krawl.model.agent import Agent, Organization
from krawl.model.hosting_unit import HostingUnitId
# from krawl.model.util import parse_date
from krawl.model.licenses import License
from krawl.model.sourcing_procedure import SourcingProcedure


@dataclass(slots=True)
class CrawlingMeta:  # pylint: disable=too-many-instance-attributes
    """Meta data about the crawling of the data"""

    sourcing_procedure: SourcingProcedure = None
    manifest: str | None = None  # Repo internal path or absolute HTTP(S) URLto the manifest file, if any. This is `None``, for example, if data was fetched through platform API only.
    created_at: datetime = None
    last_visited: datetime = None
    last_changed: datetime = None
    history = None
    # # internally calculated score for project importance to decide re-visit schedule
    # score: DataSet = field(default=None, init=False)


# :OHLOOMDataset
#   okh:dataProvider okhkrawl:dataProviderGithub ;
#   okh:dataSourcingProcedure okhkrawl:dataSourcingProcedureManifest ;
#   okh:okhv "OKH-LOSHv1.0"^^xsd:normalizedString ;
#   void:sparqlEndpoint <http://okh.dev.opensourceecology.de/sparql>;
#   spdx:licenseDeclared spdxl:CC-BY-SA-4.0 ;
#   #okh:licenseExpression "CC-BY-SA-4.0"^^xsd:normalizedString ;
#   dcterms:creator osegprof:jensMeisner ;
#   okh:organization osegprof:osegAssociation ;
#   # okh:timestamp "Jan 27, 2021 6:06pm GMT+0100" ;
#   okh:hasManifestFile :ManifestFile ;
#   void:rootResource :OHLOOM ;
#   dcterms:identifier "http://github.com/iop-alliance/OpenKnowHow/raw/master/res/sample_data/okh-sample-OHLOOM.ttl"^^xsd:anyURI ;
#   dcat:distribution :OHLOOMDataset-ttl ;
#   .

#   dcterms:description "The OKH triples for the OHLOOM OSH project"@en ;
#   # rdfs:subPropertyOf dcterms:rightsHolder ;
#   # rdfs:subPropertyOf schema:copyrightHolder ;
#   a okh:Dataset ;
#   rdfs:label "OHLOOM Dataset" ;
#   dcterms:conformsTo okh: ;


@dataclass(slots=True)
class DataSet:  # pylint: disable=too-many-instance-attributes
    """Meta data about one source of data
    (e.g. one repo, one hosted project or one manifest file)."""

    okhv: str = None
    crawling_meta: CrawlingMeta = None
    hosting_unit_id: HostingUnitId = None  # info about the repository on the hosting platform
    license: License = None
    creator: Agent = None  # Who created the projects meta data
    organization: Organization = None  # Who created the projects meta data

    # @classmethod
    # def from_dict(cls, data: dict) -> DataSet:
    #     if data is None:
    #         return None
    #     meta = cls()
    #     meta.hosting_unit_id = data.get("hosting-unit-id", None)  # FIXME This is an object, will probably not work like this
    #     # meta.owner = data.get("owner", None)
    #     # meta.repo = data.get("repo", None)
    #     # meta.ref = data.get("ref", None)
    #     meta.manifest_path = data.get("manifest-path", None)
    #     meta.created_at = parse_date(data.get("created-at"))
    #     meta.last_visited = parse_date(data.get("last-visited"))
    #     meta.last_changed = parse_date(data.get("last-changed"))
    #     meta.history = data.get("history", None)
    #     # meta.score = data.get("score", None)
    #     return meta

    # def as_dict(self) -> dict:
    #     return {
    #         "hosting-unit-id": self.hosting_unit_id,
    #         # "owner": self.owner,
    #         # "repo": self.repo,
    #         # "ref": self.ref,
    #         "manifest-path": self.manifest_path,
    #         "created-at": self.created_at.isoformat() if self.created_at is not None else None,
    #         "last-visited": self.last_visited.isoformat() if self.last_visited is not None else None,
    #         "last-changed": self.last_changed.isoformat() if self.last_changed is not None else None,
    #         "history": self.history,
    #         # "score": self.score,
    #     }
