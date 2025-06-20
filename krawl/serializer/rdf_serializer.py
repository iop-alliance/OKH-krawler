# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2022 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
# SPDX-FileCopyrightText: 2022 Nicolas Traeder <nicolas@konek.to>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import base64
import zlib
from datetime import datetime
from pathlib import Path
from re import sub
from typing import Callable
from urllib.parse import urlparse, urlunparse

import validators
from rdflib import DCTERMS, FOAF, OWL, RDF, RDFS, VOID, XSD, Graph, Literal, Namespace, URIRef

from krawl.errors import SerializerError
from krawl.fetcher.result import FetchResult
from krawl.log import get_child_logger
from krawl.model.agent import Agent, AgentRef, Organization, Person
from krawl.model.data_set import CrawlingMeta, DataSet
from krawl.model.file import File, Image, ImageSlot, ImageTag
from krawl.model.hosting_unit import HostingId
from krawl.model.language_string import LangStr
from krawl.model.licenses import License, LicenseCont, is_spdx_id
from krawl.model.outer_dimensions import OuterDimensions
from krawl.model.part import Part
from krawl.model.project import Project
from krawl.model.project_part_reference import Ref
from krawl.model.software import Software
from krawl.model.sourcing_procedure import SourcingProcedure
from krawl.serializer import Serializer

from .util import is_doi, is_web_url

# Useful info about RDF:
# https://medium.com/wallscope/understanding-linked-data-formats-rdf-xml-vs-turtle-vs-n-triples-eb931dbe9827

BASE_IRI_MIME = "http://www.iana.org/assignments/media-types"
BASE_IRI_SCHEMA_ORG = "https://schema.org"
# BASE_IRI_SPDX = "http://spdx.org/rdf/terms"
BASE_IRI_SPDXL = "http://spdx.org/licenses"

BASE_IRI_ODS = "http://w3id.org/oseg/ont/ods"
BASE_IRI_OKH = "http://w3id.org/oseg/ont/okh"
BASE_IRI_OKH_META = "http://w3id.org/oseg/ont/okhmeta"
BASE_IRI_OKH_KRAWLER = "http://w3id.org/oseg/ont/okhkrawl"
BASE_IRI_OKH_IMAGE = "http://w3id.org/oseg/ont/okhimg"
BASE_IRI_OTRL = "http://w3id.org/oseg/ont/otrl"
BASE_IRI_TSDC = "http://w3id.org/oseg/ont/tsdc"
BASE_IRI_TSDC_REQUIREMENTS = "http://w3id.org/oseg/ont/tsdc/requirements"

MIME = Namespace(f"{BASE_IRI_MIME}/")
SCHEMA = Namespace(f"{BASE_IRI_SCHEMA_ORG}/")
# SPDX = Namespace(f"{BASE_IRI_SPDX}#")
SPDXL = Namespace(f"{BASE_IRI_SPDXL}/")

ODS = Namespace(f"{BASE_IRI_ODS}#")
OKH = Namespace(f"{BASE_IRI_OKH}#")
OKHMETA = Namespace(f"{BASE_IRI_OKH_META}#")
OKHKRAWL = Namespace(f"{BASE_IRI_OKH_KRAWLER}#")
OKHIMG = Namespace(f"{BASE_IRI_OKH_IMAGE}#")
OTRL = Namespace(f"{BASE_IRI_OTRL}#")
TSDC = Namespace(f"{BASE_IRI_TSDC}#")
TSDCR = Namespace(f"{BASE_IRI_TSDC_REQUIREMENTS}#")
"The okh:okhv version written by this serializer"
OKHV: str = "X.X.X"  # TODO FIXME

log = get_child_logger("rdf_serializer")


class RDFSerializer(Serializer):

    @classmethod
    def extensions(cls) -> list[str]:
        return ["ttl"]

    def serialize(self, fetch_result: FetchResult, project: Project) -> tuple[str, str, str]:
        # try:
        (toml_graph, meta_graph, graph) = self._make_graph(fetch_result, project)

        toml_serialized: str = toml_graph.serialize(format="turtle", destination=None, encoding=None)
        meta_serialized: str = meta_graph.serialize(format="turtle", destination=None, encoding=None)
        serialized: str = graph.serialize(format="turtle", destination=None, encoding=None)
        # except Exception as err:
        #     raise SerializerError(f"failed to serialize RDF: {err}") from err
        return (toml_serialized, meta_serialized, serialized)

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
            case HostingId.MANIFESTS_REPO:
                data_provider = None  # TODO FIXME
            case _:
                raise SerializerError(f"Unknown hosting id {hosting_id}, trying to convert to data-provider")

        return data_provider

    @classmethod
    def _add_data_set(cls, meta_graph: Graph, namespace: Namespace, fetch_result: FetchResult,
                      project: Project) -> tuple[URIRef, URIRef]:

        name = cls._individual_case("projectDataSet")
        subj: URIRef = namespace[name]
        cls.add(meta_graph, subj, RDF.type, ODS.Dataset)
        cls.add(meta_graph, subj, RDFS.label, "Covers all the data in this namespace")

        name_src = cls._individual_case("projectDataSetSource")
        subj_src: URIRef = namespace[name_src]
        cls.add(meta_graph, subj_src, RDF.type, ODS.Source)
        cls.add(meta_graph, subj_src, RDFS.label, "Info related to the source of a data-set")

        hosting_id = fetch_result.data_set.hosting_unit_id.hosting_id()
        data_provider: URIRef = cls._data_provider(hosting_id)
        cls.add(meta_graph, subj_src, ODS.primaryHost, data_provider)

        data_sourcing_procedure_iri: URIRef
        cm: CrawlingMeta = fetch_result.data_set.crawling_meta
        sourcing_procedure = cm.sourcing_procedure
        match sourcing_procedure:
            case SourcingProcedure.API:
                data_sourcing_procedure_iri = OKHKRAWL.dataSourcingProcedureApi
            case SourcingProcedure.MANIFEST:
                data_sourcing_procedure_iri = OKHKRAWL.dataSourcingProcedureManifest
            case SourcingProcedure.GENERATED_MANIFEST:
                data_sourcing_procedure_iri = OKHKRAWL.dataSourcingProcedureGeneratedManifest
            case SourcingProcedure.DIRECT:
                data_sourcing_procedure_iri = OKHKRAWL.dataSourcingProcedureDirect
            case _:
                raise SerializerError(f"unknown data sourcing procedure: {sourcing_procedure}")
        cls.add(meta_graph, subj_src, ODS.dataSourcingProcedure, data_sourcing_procedure_iri)

        cls._add_license_and_licensor(meta_graph, False, namespace, subj, fetch_result.data_set, project.license,
                                      project.licensor, project.organization)
        cls._add_license_and_licensor(meta_graph, False, namespace, subj_src, project)

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
        if manifest_file.valid:
            manifest_file_subject = cls._add_file_info(meta_graph,
                                                       namespace,
                                                       manifest_file,
                                                       "manifestFile",
                                                       rdf_type=OKH.ManifestFile)
            cls.add(meta_graph, subj_src, OKH.hasManifestFile, manifest_file_subject)

        cls.add(meta_graph, subj_src, ODS.lastVisited, cm.last_visited)
        cls.add(meta_graph, subj_src, ODS.firstVisited, cm.first_visited)
        cls.add(meta_graph, subj_src, ODS.lastSuccessfullyVisited, cm.last_successfully_visited)
        cls.add(meta_graph, subj_src, ODS.visits, cm.visits)
        cls.add(meta_graph, subj, ODS.lastChanged, cm.last_detected_change)
        cls.add(meta_graph, subj, ODS.created, cm.created_at)
        cls.add(meta_graph, subj, ODS.changes, cm.changes)

        cls.add(meta_graph, subj_src, OKH.okhv, fetch_result.data_set.okhv_fetched
               )  # TODO Deprecated(?) - Replaced by `ODS.schemaVersionOfTheSourceData`, see below
        # The OKH-version the final, converted, serialized data follows"""
        # cls.add(graph, subj, OKH.okhvPresent, OKHV)
        cls.add(meta_graph, subj_src, ODS.schemaVersion, fetch_result.data_set.okhv_fetched)
        cls.add(meta_graph, subj_src, OKH.hasManifestFile, cm.manifest)
        # cls.add(graph, subj_src, ODS.visitsFile, cm.visits_file) # TODO
        # cls.add(graph, subj, ODS.dataFile, cm.TODO)  # TODO
        # cls.add(graph, subj, ODS.hash, cm.hash)  # TODO

        cls.add(meta_graph, subj, ODS.hasSource, subj_src)

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
        return subj, subj_src

    @staticmethod
    def _as_single_path_part(raw_part: str) -> str:
        # return quote(raw_part)
        if raw_part.startswith("/"):
            raw_part = raw_part[1:]
        return raw_part.replace("/", "__")

    @staticmethod
    def _make_project_namespace(project: Project) -> Namespace:
        parts = urlparse(project.repo)
        singularized_path: str = RDFSerializer._as_single_path_part(str(parts.path))
        raw_path: Path
        if project.version:
            raw_path = Path(project.version.replace(" ", "_"), singularized_path)
        else:
            raw_path = Path(singularized_path)
        # path: str = RDFSerializer._as_single_path_part(str(raw_path)) + "/"
        path: str = str(raw_path) + "/"
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
    def _make_OTRL(project: Project) -> str | None:
        v = project.technology_readiness_level
        if v is None:
            return None
        otrl_manifest = getattr(OTRL, v)
        return otrl_manifest.replace('OTRL-', 'OTRL')

    @staticmethod
    def _make_ODRL(project: Project) -> str | None:
        v = project.documentation_readiness_level
        if v is None:
            return None
        odrl_manifest = getattr(OTRL, v)  # NOTE: Yes, ODRL is in the OTRL namespace too!
        return odrl_manifest.replace('ODRL-', 'ODRL').replace('*', 'Star')

    @staticmethod
    def _capitalize(s: str) -> str:
        if s == "":
            return s
        else:
            return s[0].upper() + s[1:]

    @staticmethod
    def _decapitalize(s: str) -> str:
        if s == "":
            return s
        else:
            return s[0].lower() + s[1:]

    @staticmethod
    def _title_case(s: str) -> str:
        parts = s.split(" ")
        capitalized = "".join([RDFSerializer._capitalize(p) for p in parts if p != ""])
        alpha_num = "".join([cap for cap in capitalized if cap.isalnum() or cap == "_" or cap == "-"])
        return alpha_num

    @staticmethod
    def _individual_case(s: str) -> str:
        """In RDF, the convention is for individuals to start with a lower case character."""
        title_cased = RDFSerializer._title_case(s)
        return title_cased[0].lower() + title_cased[1:]

    @staticmethod
    def _camel_case(s: str) -> str:
        # parts = s.split("-")
        # without_dash = "".join([parts[0]] + [p.capitalize() for p in parts[1:]])
        # return without_dash
        s = sub(r"(_|-)+", " ", s).title().replace(" ", "")
        return ''.join([s[0].lower(), s[1:]])

    @staticmethod
    def _upper_camel_case(s: str) -> str:
        return RDFSerializer._capitalize(RDFSerializer._camel_case(s))

    @staticmethod
    def add(graph: Graph,
            subject: URIRef,
            predicate: URIRef,
            object: str | LangStr | URIRef | Literal | datetime | float | None,
            datatype: URIRef | None = None):
        if object:
            if not isinstance(object, (URIRef, Literal)):
                if isinstance(object, str) and object.startswith("http") and validators.url(object):
                    object = URIRef(object)
                elif isinstance(object, LangStr):
                    object = Literal(str(object.text), lang=object.language)
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
    def add_outer_dimensions(cls, graph: Graph, subject: URIRef, outer_dimensions: OuterDimensions):
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
        add_if_exists_fallback(thing, OKH.material, "material")
        add_if_exists_fallback(thing, OKH.manufacturingProcess, "manufacturing_process")
        cls.add(graph, part_subject, OKH.hasMass, thing.mass, XSD.float)

        if thing.outer_dimensions is not None:
            outer_dimensions = namespace[cls._individual_case(f"{part_name}OuterDimensions")]
            cls.add(graph, part_subject, OKH.hasOuterDimensions, outer_dimensions)
            cls.add(graph, outer_dimensions, RDF.type, OKH.Dimensions)
            cls.add(graph, outer_dimensions, RDFS.label, f"Outer Dimensions of {thing.name}")
            cls.add_outer_dimensions(graph, outer_dimensions, thing.outer_dimensions)

        if thing.tsdc is not None:
            # TODO Parse TsDCs, and check if part.tsdc is a valid tsdc, but maybe do that earlier in the process, not here, while serializing
            cls.add(graph, part_subject, OKH.tsdc, URIRef(f"{BASE_IRI_TSDC}#{thing.tsdc}"))

        # sources
        cls._add_files(graph,
                       namespace=namespace,
                       project=project,
                       parent_subj=part_subject,
                       parent_association_property=OKH.hasSource,
                       files=thing.source,
                       entity_name="SourceFile",
                       parent_name=part_name)

        # exports
        cls._add_files(graph,
                       namespace=namespace,
                       project=project,
                       parent_subj=part_subject,
                       parent_association_property=OKH.hasExport,
                       files=thing.export,
                       entity_name="ExportFile",
                       parent_name=part_name)

        # auxiliaries
        cls._add_files(graph,
                       namespace=namespace,
                       project=project,
                       parent_subj=part_subject,
                       parent_association_property=OKH.hasAuxiliary,
                       files=thing.auxiliary,
                       entity_name="AuxiliaryFile",
                       parent_name=part_name)

        # images
        cls._add_files(graph,
                       namespace=namespace,
                       project=project,
                       parent_subj=part_subject,
                       parent_association_property=OKH.hasImage,
                       files=thing.image,
                       entity_name="Image",
                       parent_name=part_name,
                       rdf_type=OKH.Image,
                       extras_handler=cls.image_extras_handler)

        return part_subject

    @classmethod
    def _add_parts(cls, graph, namespace: Namespace, project) -> list[URIRef]:

        part_subjects = []
        for part in project.part:
            part_name_clean = cls._individual_case(part.name_clean if part.name_clean !=
                                                   "project" else part.name_clean + "_part")
            part_subject: URIRef = namespace[part_name_clean]
            cls.add(graph, part_subject, RDF.type, OKH.Part)
            cls.add(graph, part_subject, OKH.name, part.name)

            part_subject = cls._fill_part(graph, namespace, project, part, part_name_clean, part_subject)

            part_subjects.append(part_subject)

        return part_subjects

    @classmethod
    def _create_publication(cls, graph: Graph, namespace: Namespace, rdf_name: str, doi_or_url: str) -> URIRef:

        subj = namespace[rdf_name]
        # We only create this individual if it is not yet in the graph
        if (subj, None, None) not in graph:
            if is_doi(doi_or_url):
                cls.add(graph, subj, OKH.doi, doi_or_url)
            elif is_web_url(doi_or_url):
                cls.add(graph, subj, ODS.url, doi_or_url)
            else:
                log.warn(
                    f"Ignoring publication entry, because it is neither a DOI nor a common web URL: '{doi_or_url}'")
                return subj
            cls.add(graph, subj, RDF.type, OKH.Publication)
        return subj

    @classmethod
    def _create_standard(cls, graph: Graph, namespace: Namespace, rdf_name: str, standard: str) -> URIRef:

        subj = namespace[rdf_name]
        # We only create this individual if it is not yet in the graph
        if (subj, None, None) not in graph:
            cls.add(graph, subj, RDF.type, OKH.Standard)
            cls.add(graph, subj, OKH.standardID, standard)
        return subj

    @classmethod
    def _create_software(cls, graph: Graph, namespace: Namespace, rdf_name: str, software: Software) -> URIRef:

        subj = namespace[rdf_name]
        # We only create this individual if it is not yet in the graph
        if (subj, None, None) not in graph:
            cls.add(graph, subj, RDF.type, OKH.Software)
            cls.add(graph, subj, OKH.release, software.release)
            if software.documentation_language:
                for doc_lang in software.documentation_language:
                    cls.add(graph, subj, OKH.documentationLanguage, doc_lang)
            cls._add_license_and_licensor(graph, True, namespace, subj, software)
        return subj

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
    def _create_person(cls,
                       graph: Graph,
                       namespace: Namespace,
                       rdf_name: str,
                       person: Person | AgentRef,
                       store: bool = False) -> URIRef:

        if isinstance(person, AgentRef):
            subj = URIRef(person.iri)
        else:
            subj = namespace[rdf_name]  # TODO FIXME This whole method
            # We only create this individual if it is not yet in the graph
            if store and (subj, None, None) not in graph:
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
    def _create_organization(cls,
                             graph: Graph,
                             namespace: Namespace,
                             rdf_name: str,
                             org: Organization | AgentRef,
                             store: bool = False) -> URIRef:

        if isinstance(org, AgentRef):
            subj = URIRef(org.iri)
        else:
            subj = namespace[rdf_name]  # TODO FIXME This whole method
            # We only create this individual if it is not yet in the graph
            if store and (subj, None, None) not in graph:
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
    def _create_agent(cls,
                      graph: Graph,
                      namespace: Namespace,
                      rdf_name: str,
                      agent: Agent | AgentRef,
                      store: bool = False) -> URIRef:
        # subj = namespace[rdf_name]  # TODO FIXME This whole method

        subj: URIRef
        if isinstance(agent, AgentRef):
            subj = URIRef(agent.iri)
        if isinstance(agent, Person):
            subj = cls._create_person(graph, namespace, rdf_name, agent, store)
        elif isinstance(agent, Organization):
            subj = cls._create_organization(graph, namespace, rdf_name, agent, store)
        else:
            raise TypeError(f"Unknown agent type: {type(agent)}")
        return subj

    @classmethod
    def _add_license_and_licensor(
        cls,
        graph: Graph,
        store_agents: bool,
        namespace: Namespace,
        subj: URIRef,
        project: Project | Software | DataSet,
        license_docu: LicenseCont | None = None,
        licensor_docu: list[Agent | AgentRef] = [],
        organization_docu: list[Organization | AgentRef] = [],
    ):

        if project.license:
            license_cont: LicenseCont | Ref = project.license
            license_id: License
            if isinstance(license_cont, LicenseCont):
                license_id = license_cont.id()
            elif isinstance(license_cont, Ref):
                if not license_docu:
                    raise ValueError(
                        "data-set license is marked as being the same as the docu license, but no docu license was provided"
                    )
                license_id = license_docu.id()
            else:
                raise TypeError(f"Unknown license type: {type(license_cont)} - content:\n{license_cont}")
            # if project.license.is_spdx:
            if is_spdx_id(license_id):
                cls.add(graph, subj, ODS.license, SPDXL[license_id])
            elif license_id == "LicenseRef-NONE" or license_id == "LicenseRef-NOASSERTION":
                cls.add(graph, subj, ODS.license, OKHKRAWL.NoAssertionLicense)
            elif license_id == "LicenseRef-AllRightsReserved":
                cls.add(graph, subj, ODS.license, OKHKRAWL.AllRightsReservedLicense)
            else:
                cls.add(graph, subj, ODS.licenseExpression, license_id)
        if project.licensor:
            licensors: list[Agent | AgentRef]
            if isinstance(project.licensor, Ref):
                licensors = licensor_docu
            else:
                licensors = project.licensor
            for (index, licensor) in enumerate(licensors):
                internal_iri_name = f"licensor{index}"
                agent_rdf_iri = cls._create_agent(graph, namespace, internal_iri_name, licensor, store=store_agents)
                cls.add(graph, subj, ODS.licensor, agent_rdf_iri)
        if project.organization:
            orgs: list[Organization | AgentRef]
            if isinstance(project.organization, Ref):
                orgs = organization_docu
            else:
                orgs = project.organization
            for (index, organization) in enumerate(orgs):
                internal_iri_name = f"organization{index}"
                org_rdf_iri = cls._create_organization(graph,
                                                       namespace,
                                                       internal_iri_name,
                                                       organization,
                                                       store=store_agents)
                cls.add(graph, subj, OKH.organization, org_rdf_iri)

    @classmethod
    def _add_project(cls, graph: Graph, namespace: Namespace, fetch_result: FetchResult, project: Project) -> URIRef:
        module_name = 'project'
        module_subject = namespace[module_name]
        cls.add(graph, module_subject, RDF.type, OKH.Module)

        cls.add(graph, module_subject, OKH.name, project.name)
        # NOTE That is not how this works. It would have to link to an RDF subject (by IRI) that represents the same module but un-frozen/non-permanent. IT would likely be in an other file.
        #cls.add(graph, module_subject, OKH.versionOf, project.repo)
        cls.add(graph, module_subject, ODS.source, project.repo)

        # TODO FIXME This next line is not really correct, but it needs changes elsewhere (probably even the manifest and/or ontology) to be done right
        # hosting_id = fetch_result.data_set.hosting_unit_id.hosting_id()
        # NOTE The following we only have in the dataset (in meta.ttl)
        # cls.add(graph, module_subject, ODS.host, cls._data_provider(hosting_id))
        cls.add(graph, module_subject, OKH.version, project.version)
        cls.add(graph, module_subject, OKH.release, project.release)

        cls._add_license_and_licensor(graph, True, namespace, module_subject, project)

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
        for (index, doi_or_url) in enumerate(project.publication):
            internal_iri_name = f"publication{index}"
            publication_rdf_iri = cls._create_publication(graph, namespace, internal_iri_name, doi_or_url)
            cls.add(graph, module_subject, OKH.hasPublication, publication_rdf_iri)
        for (index, standard) in enumerate(project.standard_compliance):
            internal_iri_name = f"standard{index}"
            standard_rdf_iri = cls._create_standard(graph, namespace, internal_iri_name, standard)
            cls.add(graph, module_subject, OKH.compliesWith, standard_rdf_iri)
        for (index, software) in enumerate(project.software):
            internal_iri_name = f"software{index}"
            software_rdf_iri = cls._create_software(graph, namespace, internal_iri_name, software)
            cls.add(graph, module_subject, OKH.hasSoftware, software_rdf_iri)

        cls._fill_part(graph, namespace, project, project, module_name, module_subject)

        cls._add_files(graph,
                       namespace=namespace,
                       project=project,
                       parent_subj=module_subject,
                       parent_association_property=OKH.hasManufacturingInstructions,
                       files=project.manufacturing_instructions,
                       entity_name="ManufacturingInstructions",
                       parent_name=module_name)

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
        # We only create this individual if it is not yet in the graph
        if (subj, None, None) not in graph:
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

    @classmethod
    def _add_files(cls,
                   graph,
                   namespace: Namespace,
                   project: Project,
                   parent_subj: URIRef,
                   parent_association_property: URIRef,
                   files: list[File] | list[Image] | None,
                   entity_name: str,
                   parent_name: str | None = None,
                   rdf_type: URIRef = ODS.File,
                   extras_handler: Callable | None = None) -> None:
        if files is None:
            return
        if parent_name:
            entity_name_base = f"{RDFSerializer._decapitalize(parent_name)}{RDFSerializer._capitalize(entity_name)}"
        else:
            entity_name_base = f"{RDFSerializer._decapitalize(entity_name)}"
        for i, file in enumerate(files):
            subj = cls._add_file_info(graph,
                                      namespace,
                                      file,
                                      entity_name=cls._individual_case(f"{entity_name_base}{i + 1}"),
                                      parent_name=parent_name,
                                      rdf_type=rdf_type,
                                      extras_handler=extras_handler)
            cls.add(graph, parent_subj, parent_association_property, subj)

    @staticmethod
    def _image_slot(slot: ImageSlot) -> URIRef:
        return URIRef(f"{BASE_IRI_OKH_IMAGE}#slot{RDFSerializer._upper_camel_case(str(slot))}")

    @staticmethod
    def _image_tag(tag: ImageTag) -> URIRef:
        return URIRef(f"{BASE_IRI_OKH_IMAGE}#tag{RDFSerializer._upper_camel_case(str(tag))}")

    @staticmethod
    def image_extras_handler(graph, _namespace: Namespace, file: File, _entity_name: str, subj: URIRef) -> None:
        if isinstance(file, Image):
            for slot in file.slots:
                okh_rdf_image_slot = RDFSerializer._image_slot(slot)
                RDFSerializer.add(graph, subj, OKH.fillsSlot, okh_rdf_image_slot)
            for tag in file.tags:
                okh_rdf_image_tag = RDFSerializer._image_tag(tag)
                RDFSerializer.add(graph, subj, OKH.hasTag, okh_rdf_image_tag)
            for depicts in file.depicts:
                RDFSerializer.add(graph, subj, OKH.depicts, depicts)

    @classmethod
    def _setup_graph(cls, graph: Graph, meta: bool = False) -> None:
        if not meta:
            graph.bind("mime", MIME)
            # graph.bind("okhmeta", OKHMETA)
            graph.bind("okhimg", OKHIMG)
            graph.bind("otrl", OTRL)
            graph.bind("tsdc", TSDC)
            # graph.bind("tsdcr", TSDCR)
        graph.bind("ods", ODS)
        graph.bind("rdfs", RDFS)
        graph.bind("okh", OKH)
        graph.bind("okhkrawl", OKHKRAWL)
        graph.bind("owl", OWL)
        graph.bind("schema", SCHEMA)
        # graph.bind("spdx", SPDX)
        graph.bind("spdxl", SPDXL)
        graph.bind("xsd", XSD)

    @classmethod
    def _make_graph(cls, fetch_result: FetchResult, project: Project) -> tuple[Graph, Graph, Graph]:
        namespace = cls._make_project_namespace(project)

        toml_graph: Graph = Graph()
        cls._setup_graph(toml_graph, meta=True)
        toml_graph.bind("", namespace)

        meta_graph: Graph = Graph()
        cls._setup_graph(meta_graph, meta=True)
        meta_graph.bind("", namespace)

        graph: Graph = Graph()
        cls._setup_graph(graph, meta=False)
        graph.bind("", namespace)

        # NOTE The data-set is the top of the data tree within a manifest,
        #      similar to an `owl:Ontology` in case of a vocabulary.
        #      As it will likely change more often then the actual OKH data,
        #      because at least `lastVisited` gets updated each time we fetch it,
        #      we store it in a separate file then the actual OKH RDF,
        #      which only changes when the actual fetched OKH data
        #      differs from previous fetches.
        data_set_subj, subj_src = cls._add_data_set(meta_graph, namespace, fetch_result, project)

        module_subject = cls._add_project(graph, namespace, fetch_result, project)

        if project.normalized_toml:
            compressed_normalized_manifest_toml_content: bytes = zlib.compress(
                bytearray(project.normalized_toml, 'utf-8'), zlib.Z_BEST_COMPRESSION)
            b64_bytes: bytes = base64.b64encode(compressed_normalized_manifest_toml_content)
            b64_str: str = b64_bytes.decode('utf-8')
            cls.add(toml_graph, module_subject, OKH.normalizedManifestContent, b64_str)

        cls.add(meta_graph, data_set_subj, VOID.rootResource, module_subject)

        cls.add(graph, module_subject, ODS.hasSource, subj_src)

        cls._add_files(graph,
                       namespace=namespace,
                       project=project,
                       parent_subj=module_subject,
                       parent_association_property=OKH.hasReadme,
                       files=project.readme,
                       entity_name="readme",
                       parent_name=project.name)

        cls._add_files(graph,
                       namespace=namespace,
                       project=project,
                       parent_subj=module_subject,
                       parent_association_property=OKH.hasBoM,
                       files=project.bom,
                       entity_name="billOfMaterials",
                       parent_name=project.name)

        cls._add_files(graph,
                       namespace=namespace,
                       project=project,
                       parent_subj=module_subject,
                       parent_association_property=OKH.hasUserManual,
                       files=project.user_manual,
                       entity_name="userManual",
                       parent_name=project.name)

        part_subjects = cls._add_parts(graph, namespace, project)
        for part_subject in part_subjects:
            cls.add(graph, module_subject, OKH.hasComponent, part_subject)

        return (toml_graph, meta_graph, graph)
