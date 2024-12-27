from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from krawl.model.agent import Agent, Organization
from krawl.model.hosting_unit import HostingUnitId
from krawl.model.licenses import License
from krawl.model.sourcing_procedure import SourcingProcedure


@dataclass(slots=True)
class CrawlingMeta:  # pylint: disable=too-many-instance-attributes
    """Meta data about the crawling of the data"""

    sourcing_procedure: SourcingProcedure
    last_visited: datetime
    manifest: str | None = None  # Repo internal path or absolute HTTP(S) URLto the manifest file, if any. This is `None``, for example, if data was fetched through platform API only.
    created_at: datetime | None = None
    last_changed: datetime | None = None
    # history = None
    # # internally calculated score for project importance to decide re-visit schedule
    # score: float = field(default=None, init=False)


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

    okhv: str
    crawling_meta: CrawlingMeta
    hosting_unit_id: HostingUnitId
    """info about the repository on the hosting platform"""
    license: License
    creator: Agent
    """Who created the projects meta data"""
    organization: Organization | None = None
    """Who created the projects meta data"""
