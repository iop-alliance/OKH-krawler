# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from krawl.model.agent import Agent, Organization
from krawl.model.hosting_unit import HostingUnitId
from krawl.model.licenses import License
from krawl.model.project_part_reference import Ref
from krawl.model.sourcing_procedure import SourcingProcedure


@dataclass(slots=True)
class CrawlingMeta:  # pylint: disable=too-many-instance-attributes
    """Meta data about the crawling of the data"""

    sourcing_procedure: SourcingProcedure
    # last_state: ScrapingIntentResultState
    last_visited: datetime | None
    first_visited: datetime | None = None
    last_successfully_visited: datetime | None = None
    # last_changed: datetime | None = None
    last_detected_change: datetime | None = None
    created_at: datetime | None = None
    """This differs from `first_visited`,
    if we know when before our first visit that the data was created
    on the hosting technology."""
    visits: int = 1
    changes: int = 0
    manifest: str | None = None
    """Repo internal path or absolute HTTP(S) URL to the manifest file, if any.
    This is `None``, for example, if data was fetched through platform API only."""
    # visits_file: Path | None = None
    # history = None
    # score: float = field(default=None, init=False)
    # """internally calculated score for project importance to decide re-visit schedule"""


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

    okhv_fetched: str
    """The OKH-version the original (fetched/crawled) data follows"""
    crawling_meta: CrawlingMeta
    hosting_unit_id: HostingUnitId
    """info about the repository on the hosting platform"""
    license: License | Ref
    creator: Agent | Ref
    """Who created the projects meta data"""
    organization: Organization | Ref | None = None
    """Who created the projects meta data"""
