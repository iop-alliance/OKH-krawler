# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2022 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
# SPDX-FileCopyrightText: 2022 Nicolas Traeder <nicolas@konek.to>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import quote, urlparse, urlunparse

import validators
from rdflib import DCTERMS, FOAF, OWL, RDF, RDFS, VOID, XSD, Graph, Literal, Namespace, URIRef

from krawl.errors import SerializerError
from krawl.fetcher.result import FetchResult
from krawl.model.agent import Agent, AgentRef, Organization, Person
from krawl.model.dataset import CrawlingMeta
from krawl.model.file import File, Image, ImageSlot, ImageTag
from krawl.model.hosting_unit import HostingId
from krawl.model.licenses import License
from krawl.model.part import Part
from krawl.model.project import Project
from krawl.model.sourcing_procedure import SourcingProcedure
from krawl.serializer import Serializer

# Useful info about RDF:
# https://medium.com/wallscope/understanding-linked-data-formats-rdf-xml-vs-turtle-vs-n-triples-eb931dbe9827

BASE_IRI_MIME = "http://www.iana.org/assignments/media-types"
BASE_IRI_SCHEMA_ORG = "https://schema.org"
BASE_IRI_SPDX = "http://spdx.org/rdf/terms"

BASE_IRI_ODS = "http://w3id.org/oseg/ont/ods"
BASE_IRI_OKH = "http://w3id.org/oseg/ont/okh"
BASE_IRI_OKH_META = "http://w3id.org/oseg/ont/okhmeta"
BASE_IRI_OKH_KRAWLER = "http://w3id.org/oseg/ont/okhkrawl"
BASE_IRI_OTRL = "http://w3id.org/oseg/ont/otrl"
BASE_IRI_TSDC = "http://w3id.org/oseg/ont/tsdc"
BASE_IRI_TSDC_REQUIREMENTS = "http://w3id.org/oseg/ont/tsdc/requirements"

MIME = Namespace(f"{BASE_IRI_MIME}/")
SCHEMA = Namespace(f"{BASE_IRI_SCHEMA_ORG}/")
SPDX = Namespace(f"{BASE_IRI_SPDX}#")

ODS = Namespace(f"{BASE_IRI_ODS}#")
OKH = Namespace(f"{BASE_IRI_OKH}#")
OKHMETA = Namespace(f"{BASE_IRI_OKH_META}#")
OKHKRAWL = Namespace(f"{BASE_IRI_OKH_KRAWLER}#")
OTRL = Namespace(f"{BASE_IRI_OTRL}#")
TSDC = Namespace(f"{BASE_IRI_TSDC}#")
TSDCR = Namespace(f"{BASE_IRI_TSDC_REQUIREMENTS}#")
"The okh:okhv version written by this serializer"
OKHV: str = "X.X.X"


class RDFSerializer(Serializer):

    @classmethod
    def extensions(cls) -> list[str]:
        return ["ttl"]

    def serialize(self, fetch_result: FetchResult, project: Project) -> str:
        # try:
        graph = self._make_graph(fetch_result, project)

        serialized: str = graph.serialize(format="turtle", destination=None, encoding=None)
        # except Exception as err:
        #     raise SerializerError(f"failed to serialize RDF: {err}") from err
        return serialized

    @classmethod
    def _data_provider(cls, hosting_id: HostingId) -> URIRef:
        data_provider: URIRef
        match hosting_id:
            case HostingId.APPROPEDIA_ORG:
                data_provider = OKHKRAWL.dataProviderAppropedia
            case HostingId.CODEBERG_ORG:
                data_provider = OKHKRAWL.dataProviderCodeberg
            case HostingId.GITHUB_COM:
                data_provider = OKHKRAWL.dataProviderGithub
            case HostingId.GITLAB_COM:
                data_provider = OKHKRAWL.dataProviderGitlab
            case HostingId.GITLAB_OPENSOURCEECOLOGY_DE:
                data_provider = OKHKRAWL.dataProviderGitlabOpenSourceEcologyGermany
            case HostingId.OSHWA_ORG:
                data_provider = OKHKRAWL.dataProviderOshwa
            case HostingId.THINGIVERSE_COM:
                data_provider = OKHKRAWL.dataProviderThingiverse
            case _:
                raise SerializerError(f"Unknown hosting id {hosting_id}, trying to convert to data-provider")

        return data_provider

    @classmethod
    def _add_data_set(cls, graph: Graph, namespace: Namespace, fetch_result: FetchResult, project: Project) -> URIRef:
        name = cls._individual_case(project.name + "_DataSet")

        subj: URIRef = namespace[name]
        cls.add(graph, subj, RDF.type, ODS.Dataset)
        cls.add(graph, subj, RDFS.label, "Covers all the data in this namespace")

        hosting_id = fetch_result.data_set.hosting_unit_id.hosting_id()
        data_provider: URIRef = cls._data_provider(hosting_id)
        cls.add(graph, subj, ODS.dataProvider, data_provider)

        data_sourcing_procedure_iri: URIRef
        cm: CrawlingMeta = fetch_result.data_set.crawling_meta
        sourcing_procedure = cm.sourcing_procedure
        match sourcing_procedure:
            case SourcingProcedure.API:
                data_sourcing_procedure_iri = OKHKRAWL.dataSourcingProcedureApi
            case SourcingProcedure.MANIFEST:
                data_sourcing_procedure_iri = OKHKRAWL.dataSourcingProcedureGeneratedManifest
            case SourcingProcedure.GENERATED_MANIFEST:
                data_sourcing_procedure_iri = OKHKRAWL.dataSourcingProcedureManifest
            case SourcingProcedure.DIRECT:
                data_sourcing_procedure_iri = OKHKRAWL.dataSourcingProcedureDirect
            case _:
                raise SerializerError(f"unknown data sourcing procedure: {sourcing_procedure}")
        cls.add(graph, subj, ODS.dataSourcingProcedure, data_sourcing_procedure_iri)

        cls.add(graph, subj, OKH.okhvOriginal, fetch_result.data_set.okhv_fetched)
        # The OKH-version the final, converted, serialized data follows"""
        cls.add(graph, subj, OKH.okhvPresent, OKHV)

        # manifest_file_subject = cls._add_file(
        #     graph=graph,
        #     namespace=namespace,
        #     project=project,
        #     key="manifest",
        #     entity_name="manifestFile",
        #     rdf_type=OKH.ManifestFile,
        # )
        manifest_file = File(url=fetch_result.data_set.crawling_meta.manifest, name="OKH Manifest")
        manifest_file.mime_type = manifest_file.evaluate_mime_type()
        manifest_file_subject = cls._add_file_info(graph,
                                                   namespace,
                                                   manifest_file,
                                                   "manifestFile",
                                                   rdf_type=OKH.ManifestFile)

        # internal_iri_name = f"dataset_licensor"
        # agent_rdf_iri = cls._create_agent(graph, namespace, internal_iri_name, licensor)
        # cls.add(graph, module_subject, OKH.licensor, agent_rdf_iri)

        cls.add(graph, subj, ODS.lastVisited, cm.last_visited)
        cls.add(graph, subj, ODS.lastChanged, cm.last_changed)
        cls.add(graph, subj, ODS.created, cm.created_at)

        # data_set = DataSet(
        #     crawling_meta=CrawlingMeta(
        #         sourcing_procedure=__sourcing_procedure__,
        #         # created_at: datetime = None
        #         last_visited=last_visited,
        #         # last_changed: datetime = None
        #         # history = None,
        #     ),
        #     hosting_unit_id=hosting_unit_id,
        #     license=__dataset_license__,
        #     creator=__dataset_creator__,
        # )
        cls.add(graph, subj, OKH.hasManifestFile, manifest_file_subject)

        # # cls.add(graph, module_subject, ODS.dataSourcingProcedure, project.data_sourcing_procedure)
        # parts = urlparse(project.repo)
        # base = urlunparse(components=(
        #     parts.scheme,
        #     parts.netloc,
        #     quote(str(Path(parts.path, project.version))) + "/",
        #     "",
        #     "",
        #     "",
        # ))
        return subj

    @staticmethod
    def _make_project_namespace(project: Project) -> Namespace:
        parts = urlparse(project.repo)
        path: str
        if project.version:
            path = quote(str(Path(parts.path, project.version))) + "/"
        else:
            path = quote(str(Path(parts.path))) + "/"
        base = urlunparse(components=(
            parts.scheme,
            parts.netloc,
            path,
            "",
            "",
            "",
        ))
        return Namespace(base)

    @staticmethod
    def _make_OTRL(project):
        v = project.technology_readiness_level
        if v is None:
            return None
        otrl_manifest = getattr(OTRL, v)
        return otrl_manifest.replace('OTRL-', 'OTRL')

    @staticmethod
    def _make_ODRL(project):
        v = project.documentation_readiness_level
        if v is None:
            return None
        odrl_manifest = getattr(OTRL, v)  # NOTE: Yes, ODRL is in the OTRL namespace too!
        return odrl_manifest.replace('ODRL-', 'ODRL').replace('*', 'Star')

    @staticmethod
    def _title_case(s):
        parts = s.split(" ")
        capitalized = "".join([p.capitalize() for p in parts])
        alpha_num = "".join([cap for cap in capitalized if cap.isalnum()])
        return alpha_num

    @staticmethod
    def _individual_case(s):
        """In RDF, the convention is for individuals to start with a lower case character."""
        title_cased = RDFSerializer._title_case(s)
        return title_cased[0].lower() + title_cased[1:]

    @staticmethod
    def _camel_case(s):
        parts = s.split("-")
        without_dash = "".join([parts[0]] + [p.capitalize() for p in parts[1:]])
        return without_dash

    @staticmethod
    def add(graph: Graph,
            subject: URIRef,
            predicate: URIRef,
            object: str | URIRef | Literal | datetime | float | None,
            datatype: URIRef | None = None):
        if object:
            if not isinstance(object, (URIRef, Literal)):
                if isinstance(object, str) and object.startswith("http") and validators.url(object):
                    object = URIRef(object)
                elif isinstance(object, datetime):
                    object = Literal(object.isoformat(), datatype=datatype if datatype else XSD.dateTime)
                elif isinstance(object, float):
                    object = Literal(str(object), datatype=datatype if datatype else XSD.float)
                else:
                    if datatype:
                        object = Literal(str(object), datatype=datatype)
                    else:
                        object = Literal(str(object))
            graph.add((subject, predicate, object))

    @classmethod
    def _add_file_link(cls, graph: Graph, subject: URIRef, file: File):
        if file.path:
            cls.add(graph, subject, ODS.relativePath, str(file.path))
        if file.url:
            cls.add(
                graph, subject, ODS.url, file.url
            )  # TODO Maybe use file.permaURL instead here, because according to the spec/Ontology as of Dec. 2022), this is supposed to be a permanent/frozen URL -> NO, change the spec! We removed permaURL, and rather want to have a frozen and a separate, unfrozen version of the whole manifest.
        # NOTE This is not part of the spec (as of December 2022), and fileURL is mentioned in the spec to contain the permanent URL; related issue: https://github.com/iop-alliance/OpenKnowHow/issues/132
        # cls.add(graph, subject, ODS.permaURL, file.perma_url)
        if file.mime_type:
            mime_uri = MIME[file.mime_type]
            cls.add(graph, subject, ODS.fileFormat, mime_uri)
        # cls.add(graph, subject, ODS.mimeType, file.mime_type) # FIXME: only add if contained in ontology
        # cls.add(graph, subject, ODS.created, file.created_at) # FIXME: only add if contained in ontology
        # cls.add(graph, subject, ODS.lastChanged, file.last_changed) # FIXME: only add if contained in ontology
        # cls.add(graph, subject, ODS.lastVisited, file.last_visited) # FIXME: only add if contained in ontology

    @classmethod
    def add_outer_dimensions(cls, graph, subject, outer_dimensions):
        cls.add(graph, subject, OKH.width, outer_dimensions.width)
        cls.add(graph, subject, OKH.height, outer_dimensions.height)
        cls.add(graph, subject, OKH.depth, outer_dimensions.depth)

    @classmethod
    def _fill_part(cls, graph, namespace: Namespace, project: Project, thing: Project | Part, part_name: str,
                   part_subject: URIRef) -> URIRef:
        """This fills a part with life.
        NOTE That everything added in here is shared between Module and Part,
        so we use it for both."""

        def add_if_exists_fallback(thing: Project | Part,
                                   property: URIRef,
                                   key: str,
                                   datatype: URIRef | None = None) -> None:
            if hasattr(thing, key):
                cls.add(graph, part_subject, property, getattr(thing, key), datatype)

        def get_fallback(thing: Project | Part, key: str):
            if hasattr(thing, key):
                value = getattr(thing, key)
                if value:
                    return value
            return getattr(project, key)

        documentation_language: list[str] = get_fallback(thing, "documentation_language")
        for doc_lang in documentation_language:
            cls.add(graph, part_subject, OKH.documentationLanguage, doc_lang)
        # license: License = get_fallback(thing, "license")
        # if license:
        #     if license.is_spdx:
        #         cls.add(graph, part_subject, ODS.license, SPDX[license.id()])
        #     else:
        #         cls.add(graph, part_subject, ODS.licenseExpression, license.id())
        # else:
        #     if license.reference_url:
        #         alt_license = license.reference_url[:-5]
        #     else:
        #         alt_license = license.id()
        #     cls.add(graph, part_subject, ODS.alternativeLicense,
        #             alt_license)  # FIXME: should be the license ID not the reference url, but it breaks the frontend
        # cls.add(graph, part_subject, ODS.licensor, get_fallback(thing, "licensor"))
        add_if_exists_fallback(thing, OKH.material, "material")
        add_if_exists_fallback(thing, OKH.manufacturingProcess, "manufacturing_process")
        cls.add(graph, part_subject, OKH.hasMass, thing.mass, XSD.float)

        if thing.outer_dimensions is not None:
            outer_dimensions = namespace[cls._individual_case(f"{part_name}_OuterDimensions")]
            cls.add(graph, part_subject, OKH.hasOuterDimensions, outer_dimensions)
            cls.add(graph, outer_dimensions, RDF.type, OKH.Dimensions)
            cls.add(graph, outer_dimensions, RDFS.label, f"Outer Dimensions of {thing.name}")
            cls.add_outer_dimensions(graph, outer_dimensions, thing.outer_dimensions)

        if thing.tsdc is not None:
            # TODO Parse TsDCs, and check if part.tsdc is a valid tsdc, but maybe do that earlier in the process, not here, while serializing
            cls.add(graph, part_subject, OKH.tsdc, URIRef(f"{BASE_IRI_TSDC}#{thing.tsdc}"))

        # source
        for i, file in enumerate(thing.source):
            subj = cls._add_file_info(graph,
                                      namespace,
                                      file,
                                      entity_name=cls._individual_case(f"{part_name}_source{i + 1}"),
                                      parent_name=project.name)
            cls.add(graph, part_subject, OKH.source, subj)

        # export
        for i, file in enumerate(thing.export):
            subj = cls._add_file_info(graph,
                                      namespace,
                                      file,
                                      entity_name=cls._individual_case(f"{part_name}_export{i + 1}"),
                                      parent_name=project.name)
            cls.add(graph, part_subject, OKH.export, subj)

        # auxiliary
        for i, file in enumerate(thing.auxiliary):
            subj = cls._add_file_info(graph,
                                      namespace,
                                      file,
                                      entity_name=cls._individual_case(f"{part_name}_auxiliary{i + 1}"),
                                      parent_name=project.name)
            cls.add(graph, part_subject, OKH.auxiliary, subj)

        # image
        for i, file in enumerate(thing.image):
            subj = cls._add_file_info(graph,
                                      namespace,
                                      file,
                                      entity_name=cls._individual_case(f"{part_name}_image{i + 1}"),
                                      parent_name=project.name,
                                      rdf_type=OKH.Image,
                                      extras_handler=cls.image_extras_handler)
            cls.add(graph, part_subject, OKH.hasImage, subj)

        return part_subject

    @classmethod
    def _add_parts(cls, graph, namespace: Namespace, project) -> list[URIRef]:

        part_subjects = []
        for part in project.part:
            part_name = cls._individual_case(part.name_clean if part.name_clean != project.name else part.name_clean +
                                             "_part")
            part_subject: URIRef = namespace[part_name]
            cls.add(graph, part_subject, RDF.type, OKH.Part)
            cls.add(graph, part_subject, RDFS.label, part.name)

            part_subject = cls._fill_part(graph, namespace, project, part, part_name, part_subject)

            part_subjects.append(part_subject)

        return part_subjects

    # @classmethod
    # def _create_agent(cls, graph: Graph, namespace: Namespace, rdf_name: str, agent: Agent) -> URIRef:
    #     subj = namespace[rdf_name]  # TODO FIXME This whole method

    #     if isinstance(agent, Agent):
    #         cls.add(graph, subj, RDF.type, SCHEMA.Person)
    #         cls.add(graph, subj, SCHEMA.name, agent.name)
    #         cls.add(graph, subj, SCHEMA.email, agent.email)
    #         cls.add(graph, subj, SCHEMA.url, agent.url)
    #     # if isinstance(agent, AgentRef):
    #     #     cls.add(graph, subj, RDF.type, licensor)
    #     #     cls.add(graph, subj, RDF.type, licensor)
    #     return subj

    @classmethod
    def _create_person(cls, graph: Graph, namespace: Namespace, rdf_name: str, person: Person | AgentRef) -> URIRef:

        if isinstance(person, AgentRef):
            subj = URIRef(person.iri)
        else:
            subj = namespace[rdf_name]  # TODO FIXME This whole method
            cls.add(graph, subj, RDF.type, SCHEMA.Person)
            cls.add(graph, subj, SCHEMA.name, person.name)
            cls.add(graph, subj, SCHEMA.email, person.email)
            cls.add(graph, subj, SCHEMA.url, person.url)
            cls.add(graph, subj, RDF.type, FOAF.Person)
            cls.add(graph, subj, FOAF.name, person.name)
            cls.add(graph, subj, FOAF.mbox, person.email)
            cls.add(graph, subj, FOAF.weblog, person.url)
            cls.add(graph, subj, RDF.type, DCTERMS.Agent)
        return subj

    @classmethod
    def _create_organization(cls, graph: Graph, namespace: Namespace, rdf_name: str,
                             org: Organization | AgentRef) -> URIRef:

        if isinstance(org, AgentRef):
            subj = URIRef(org.iri)
        else:
            subj = namespace[rdf_name]  # TODO FIXME This whole method
            cls.add(graph, subj, RDF.type, SCHEMA.Organization)
            cls.add(graph, subj, SCHEMA.name, org.name)
            cls.add(graph, subj, SCHEMA.email, org.email)
            cls.add(graph, subj, SCHEMA.url, org.url)
            cls.add(graph, subj, RDF.type, FOAF.Organization)
            cls.add(graph, subj, FOAF.name, org.name)
            cls.add(graph, subj, FOAF.mbox, org.email)
            cls.add(graph, subj, FOAF.weblog, org.url)
            cls.add(graph, subj, RDF.type, DCTERMS.Agent)
        return subj

    @classmethod
    def _create_agent(cls, graph: Graph, namespace: Namespace, rdf_name: str, agent: Agent | AgentRef) -> URIRef:
        # subj = namespace[rdf_name]  # TODO FIXME This whole method

        subj: URIRef
        if isinstance(agent, AgentRef):
            subj = URIRef(agent.iri)
        if isinstance(agent, Person):
            subj = cls._create_person(graph, namespace, rdf_name, agent)
        elif isinstance(agent, Organization):
            subj = cls._create_organization(graph, namespace, rdf_name, agent)
        else:
            raise TypeError(f"Unknown agent type: {type(agent)}")
        return subj

    @classmethod
    def _add_project(cls, graph: Graph, namespace: Namespace, fetch_result: FetchResult, project: Project) -> URIRef:
        module_name = 'project'
        module_subject = namespace[module_name]
        cls.add(graph, module_subject, RDF.type, OKH.Module)

        cls.add(graph, module_subject, RDFS.label, project.name)
        # NOTE That is not how this works. It would have to link to an RDF subject (by IRI) that represents the same module but un-frozen/non-permanent. IT would likely be in an other file.
        #cls.add(graph, module_subject, OKH.versionOf, project.repo)
        cls.add(graph, module_subject, ODS.source, project.repo)

        hosting_id = fetch_result.data_set.hosting_unit_id.hosting_id(
        )  # TODO FIXME This is not really correct, but it needs changes elsewhere (probably even the manifest and/or ontology) to be done right
        cls.add(graph, module_subject, ODS.host, cls._data_provider(hosting_id))
        cls.add(graph, module_subject, OKH.version, project.version)
        cls.add(graph, module_subject, OKH.release, project.release)
        # print("XXX")
        # print(type(project.license))
        if project.license:
            if project.license.is_spdx:
                cls.add(graph, module_subject, ODS.license, SPDX[project.license.id()])
            else:
                cls.add(graph, module_subject, ODS.licenseExpression, project.license.id())
        # if project.license.is_spdx:
        #     cls.add(graph, module_subject, ODS.license, project.license.id())
        # else:
        #     if project.license.reference_url is None:
        #         alt_license = project.license.id
        #     else:
        #         alt_license = project.license.reference_url[:-5]
        #     cls.add(graph, module_subject, ODS.alternativeLicense,
        #             alt_license)  # FIXME: should be the license ID not the reference url, but it breaks the frontend
        for (index, licensor) in enumerate(project.licensor):
            internal_iri_name = f"licensor{index}"
            agent_rdf_iri = cls._create_agent(graph, namespace, internal_iri_name, licensor)
            cls.add(graph, module_subject, ODS.licensor, agent_rdf_iri)
        for (index, organization) in enumerate(project.organization):
            internal_iri_name = f"organization{index}"
            org_rdf_iri = cls._create_organization(graph, namespace, internal_iri_name, organization)
            cls.add(graph, module_subject, OKH.organization, org_rdf_iri)
        # cls.add(graph, module_subject, OKH.contributorCount, None)  # TODO see if GitHub API can do this

        # graph
        for doc_lang in project.documentation_language:
            cls.add(graph, module_subject, OKH.documentationLanguage, doc_lang)
        cls.add(graph, module_subject, OKH.documentationReadinessLevel, cls._make_ODRL(project))
        cls.add(graph, module_subject, OKH.technologyReadinessLevel, cls._make_OTRL(project))
        cls.add(graph, module_subject, OKH.function, project.function)
        cls.add(graph, module_subject, OKH.cpcPatentClass, project.cpc_patent_class)
        for attestation in project.attestation:
            cls.add(graph, module_subject, OKH.attestation, attestation, datatype=XSD.anyURI)
        if project.tsdc is not None:
            # TODO Parse TsDCs, and check if part.tsdc is a valid tsdc, but maybe do that earlier in the process, not here, while serializing
            cls.add(graph, module_subject, OKH.tsdc, URIRef(f"{BASE_IRI_TSDC}#{project.tsdc}"))

        cls._fill_part(graph, namespace, project, project, module_name, module_subject)

        # NOTE We do not create a standard to then allow platform specific data again,
        #      and definitely not by introducing arbitrary properties
        #      into the OKH ontology on the fly, like we did here:
        # for index in project.specific_api_data:
        #     cls.add(graph, module_subject,
        #             URIRef(f"{BASE_IRI_OKH}#{index}"),
        #             project.specific_api_data[index])

        return module_subject

    # def _make_functional_metadata_list(self, module, functional_metadata, BASE):
    #     l = []
    #     for key, value in functional_metadata.items():
    #         keyC = self._camel_case(key)
    #         l.append((module, BASE[keyC], Literal(value)))
    #         entity = BASE[keyC]
    #         l.append((entity, RDF.type, OWL.DatatypeProperty))
    #         l.append((entity, RDFS.label, Literal(key)))
    #         l.append((entity, RDFS.subPropertyOf, OKH.functionalMetadata))
    #     return l

    # def _make_file_list(self, project, key, entity_name, rdf_type, BASE, extra=None):
    #     extra = [] if extra is None else extra
    #     parent_name = f"{project.name} {project.version}"
    #     l = []
    #     value = getattr(project, detailskey(key)) if hasattr(project, detailskey(key)) else None
    #     if value is None:
    #         return None
    #     entity = BASE[entity_name]
    #     l.append((entity, RDF.type, rdf_type))
    #     l.append((entity, RDFS.label, f"{entity_name} of {parent_name}"))
    #     for a, v in extra:
    #         l.append((entity, a, v))
    #     for k, v in value.items():
    #         l.append((entity, getattr(OKH, k), v))
    #     return entity, l

    @classmethod
    def _add_file_info(cls,
                       graph,
                       namespace: Namespace,
                       file: File,
                       entity_name: str,
                       parent_name: str | None = None,
                       rdf_type: URIRef = ODS.File,
                       extras_handler: Callable | None = None) -> URIRef:
        subj: URIRef = namespace[entity_name]
        cls.add(graph, subj, RDF.type, rdf_type)
        cls.add(graph, subj, RDFS.label, f'{entity_name} of {parent_name}' if parent_name else entity_name)
        cls._add_file_link(graph, subj, file)
        if extras_handler:
            extras_handler(graph, namespace, file, entity_name, subj)
        return subj

    @classmethod
    def _add_file(cls,
                  graph,
                  namespace: Namespace,
                  project: Project,
                  key: str,
                  entity_name: str,
                  rdf_type: URIRef = ODS.File,
                  extras_handler: Callable | None = None) -> URIRef | None:
        file = getattr(project, key) if hasattr(project, key) else None
        if file is None:
            return None

        parent_name = f"{project.name} {project.version}"
        return cls._add_file_info(graph, namespace, file, entity_name, parent_name, rdf_type, extras_handler)

    @staticmethod
    def _image_slot(slot: ImageSlot) -> URIRef:
        return URIRef(f"{BASE_IRI_OKH}#{slot}ImageSlot")  # FIXME TODO

    @staticmethod
    def _image_tag(tag: ImageTag) -> URIRef:
        return URIRef(f"{BASE_IRI_OKH}#{tag}ImageTag")  # FIXME TODO

    @staticmethod
    def image_extras_handler(graph, _namespace: Namespace, file: File, _entity_name: str, subj: URIRef) -> None:
        if isinstance(file, Image):
            for slot in file.slots:
                okh_rdf_image_slot = RDFSerializer._image_slot(slot)
                RDFSerializer.add(graph, subj, OKH.hasSlot, okh_rdf_image_slot)
            for tag in file.tags:
                okh_rdf_image_tag = RDFSerializer._image_tag(tag)
                RDFSerializer.add(graph, subj, OKH.hasTag, okh_rdf_image_tag)

    @classmethod
    def _make_graph(cls, fetch_result: FetchResult, project: Project) -> Graph:
        graph: Graph = Graph()
        graph.bind("mime", MIME)
        graph.bind("okh", OKH)
        # graph.bind("okhmeta", OKHMETA)
        graph.bind("okhkrawl", OKHKRAWL)
        graph.bind("otrl", OTRL)
        graph.bind("tsdc", TSDC)
        # graph.bind("tsdcr", TSDCR)
        graph.bind("rdfs", RDFS)
        graph.bind("owl", OWL)
        graph.bind("schema", SCHEMA)
        graph.bind("spdx", SPDX)
        graph.bind("xsd", XSD)

        namespace = cls._make_project_namespace(project)
        graph.bind("", namespace)

        # NOTE The data-set is the top of the data tree within a manifest,
        #      similar to an `owl:Ontology` in case of a vocabulary.
        data_set_subj = cls._add_data_set(graph, namespace, fetch_result, project)

        module_subject = cls._add_project(graph, namespace, fetch_result, project)
        cls.add(graph, data_set_subj, VOID.rootResource, module_subject)

        readme_subject = cls._add_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="readme",
            entity_name="readme",
        )
        if readme_subject is not None:
            cls.add(graph, module_subject, OKH.hasReadme, readme_subject)

        # image_subject = cls._add_file(
        #     graph=graph,
        #     namespace=namespace,
        #     project=project,
        #     key="image",
        #     entity_name="image",
        #     rdf_type=OKH.Image,
        #     extras_handler=cls.image_extras_handler,
        # )
        # cls.add(graph, module_subject, OKH.hasImage, image_subject)

        bom_subject = cls._add_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="bom",
            entity_name="billOfMaterials",
        )
        if bom_subject is not None:
            cls.add(graph, module_subject, OKH.hasBoM, bom_subject)

        for i, file in enumerate(project.manufacturing_instructions):
            subj = cls._add_file_info(graph,
                                      namespace,
                                      file,
                                      entity_name=cls._individual_case(f"project_manufacturingInstructions{i + 1}"),
                                      parent_name=project.name)
            cls.add(graph, module_subject, OKH.hasImage, subj)
        # manufacturing_instructions_subject = cls._add_file(
        #     graph=graph,
        #     namespace=namespace,
        #     project=project,
        #     key="manufacturing_instructions",
        #     entity_name="manufacturingInstructions",
        #     rdf_type=ODS.File,
        # )
        # if manufacturing_instructions_subject is not None:
        #     cls.add(graph, module_subject, OKH.hasManufacturingInstructions, manufacturing_instructions_subject)

        user_manual_subject = cls._add_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="user_manual",
            entity_name="userManual",
        )
        if user_manual_subject is not None:
            cls.add(graph, module_subject, OKH.hasUserManual, user_manual_subject)

        part_subjects = cls._add_parts(graph, namespace, project)
        for part_subject in part_subjects:
            cls.add(graph, module_subject, OKH.hasComponent, part_subject)

        return graph
