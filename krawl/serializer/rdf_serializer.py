# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2022 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
# SPDX-FileCopyrightText: 2022 Nicolas Traeder <nicolas@konek.to>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse

import rdflib
import validators
from rdflib import URIRef

from krawl.errors import SerializerError
from krawl.fetcher.result import FetchResult
from krawl.model.file import File
from krawl.model.hosting_unit import HostingId
from krawl.model.project import Project
from krawl.model.sourcing_procedure import SourcingProcedure
from krawl.serializer import Serializer

# Useful info about RDF:
# https://medium.com/wallscope/understanding-linked-data-formats-rdf-xml-vs-turtle-vs-n-triples-eb931dbe9827

BASE_IRI_OKH = "http://w3id.org/oseg/ont/okh"
BASE_IRI_OKH_META = "http://w3id.org/oseg/ont/okhmeta"
BASE_IRI_OKH_KRAWLER = "http://w3id.org/oseg/ont/okhkrawl"
BASE_IRI_OTRL = "http://w3id.org/oseg/ont/otrl"
BASE_IRI_TSDC = "http://w3id.org/oseg/ont/tsdc"
BASE_IRI_TSDC_REQUIREMENTS = "http://w3id.org/oseg/ont/tsdc/requirements"

OKH = rdflib.Namespace(f"{BASE_IRI_OKH}#")
OKHMETA = rdflib.Namespace(f"{BASE_IRI_OKH_META}#")
OKHKRAWL = rdflib.Namespace(f"{BASE_IRI_OKH_KRAWLER}#")
OTRL = rdflib.Namespace(f"{BASE_IRI_OTRL}#")
TSDC = rdflib.Namespace(f"{BASE_IRI_TSDC}#")
TSDCR = rdflib.Namespace(f"{BASE_IRI_TSDC_REQUIREMENTS}#")
"The okh:okhv version written by this serializer"
OKHV: str = "X.X.X"


class RDFSerializer(Serializer):

    @classmethod
    def extensions(cls) -> list[str]:
        return ["ttl"]

    def serialize(self, fetch_result: FetchResult, project: Project) -> str:
        try:
            graph = self._make_graph(fetch_result, project)

            serialized = str(graph.serialize(format="turtle").encode("utf-8"))
        except Exception as err:
            raise SerializerError(f"failed to serialize RDF: {err}") from err
        return serialized

    @classmethod
    def _add_data_set(cls, graph: rdflib.Graph, namespace: rdflib.Namespace, fetch_result: FetchResult,
                      project: Project) -> rdflib.Namespace:
        name = cls._title_case(project.name + "_DataSet")

        subj: URIRef = namespace[name]
        cls.add(graph, subj, rdflib.RDF.type, OKH.Dataset)
        cls.add(graph, subj, rdflib.RDFS.label, "Covers all the data in this namespace")

        data_provider: URIRef
        hosting_id = fetch_result.data_set.hosting_unit_id.hosting_id
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
                raise SerializerError(f"unknown hosting id: {hosting_id}")
        cls.add(graph, subj, OKH.dataProvider, data_provider)

        data_sourcing_procedure_iri: URIRef
        sourcing_procedure = fetch_result.data_set.crawling_meta.sourcing_procedure
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
        cls.add(graph, subj, OKH.dataSourcingProcedure, data_sourcing_procedure_iri)

        cls.add(graph, subj, OKH.okhv, OKHV)

        manifest_file_subject = cls._add_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="manifest_file",
            entity_name="ManifestFile",
            rdf_type=OKH.ManifestFile,
        )
        if manifest_file_subject:
            cls.add(graph, subj, OKH.hasManifestFile, manifest_file_subject)

        return subj

    @staticmethod
    def _make_project_namespace(project: Project) -> rdflib.Namespace:
        parts = urlparse(project.repo)
        base = urlunparse(components=(
            parts.scheme,
            parts.netloc,
            quote(str(Path(parts.path, project.version))) + "/",
            "",
            "",
            "",
        ))
        return rdflib.Namespace(base)

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
    def _camel_case(s):
        parts = s.split("-")
        without_dash = "".join([parts[0]] + [p.capitalize() for p in parts[1:]])
        return without_dash

    @staticmethod
    def add(graph: rdflib.Graph, subject: URIRef, predicate: URIRef, object: str | URIRef | rdflib.Literal | None, datatype: URIRef | None = None):
        if object:
            if not isinstance(object, (URIRef, rdflib.Literal)):
                if isinstance(object, str) and object.startswith("http") and validators.url(object):
                    object = rdflib.URIRef(object)
                elif isinstance(object, datetime):
                    object = rdflib.Literal(object.isoformat())
                else:
                    if datatype:
                        object = rdflib.Literal(str(object), datatype=datatype)
                    else:
                        object = rdflib.Literal(str(object))
            graph.add((subject, predicate, object))

    @classmethod
    def _add_file_link(cls, graph: rdflib.Graph, subject: URIRef, file: File):
        if file.path:
            cls.add(graph, subject, OKH.relativePath, str(file.path))
        if file.url:
            cls.add(
                graph, subject, OKH.url, file.url
            )  # TODO Maybe use file.permaURL instead here, because according to the spec/Ontology as of Dec. 2022), this is supposed to be a permanent/frozen URL -> NO, change the spec! We removed permaURL, and rather want to have a frozen and a separate, unfrozen version of the whole manifest.
        # NOTE This is not part of the spec (as of December 2022), and fileURL is mentioned in the spec to contain the permanent URL; related issue: https://github.com/iop-alliance/OpenKnowHow/issues/132
        # cls.add(graph, subject, OKH.permaURL, file.perma_url)
        cls.add(graph, subject, OKH.fileFormat,
                file.extension.upper())  # TODO We should change this to mime-type at some point
        # cls.add(graph, subject, OKH.mimeType, file.mime_type) # FIXME: only add if contained in ontology
        # cls.add(graph, subject, OKH.dateCreated, file.created_at) # FIXME: only add if contained in ontology
        # cls.add(graph, subject, OKH.dateLastChanged, file.last_changed) # FIXME: only add if contained in ontology
        # cls.add(graph, subject, OKH.dateLastVisited, file.last_visited) # FIXME: only add if contained in ontology

    @classmethod
    def add_outer_dimensions(cls, graph, subject, outer_dimensions):
        cls.add(graph, subject, OKH.width, outer_dimensions.width)
        cls.add(graph, subject, OKH.height, outer_dimensions.height)
        cls.add(graph, subject, OKH.depth, outer_dimensions.depth)

    @classmethod
    def _add_part(cls, graph, namespace: rdflib.Namespace, project) -> list[URIRef]:

        def get_fallback(part, key):
            if hasattr(part, key):
                value = getattr(part, key)
                if value is not None:
                    return value
            return getattr(project, key)

        part_subjects = []
        for part in project.part:
            part_name = cls._title_case(part.name_clean if part.name_clean != project.name else part.name_clean +
                                        "_part")

            part_subject: URIRef = namespace[part_name]
            cls.add(graph, part_subject, rdflib.RDF.type, OKH.Part)
            cls.add(graph, part_subject, rdflib.RDFS.label, part.name)

            cls.add(graph, part_subject, OKH.documentationLanguage, get_fallback(part, "documentation_language"))
            license = get_fallback(part, "license")
            if license and license.is_spdx:
                cls.add(graph, part_subject, OKH.spdxLicense, license.id)
            else:
                if license.reference_url is None:
                    alt_license = license.id
                else:
                    alt_license = license.reference_url[:-5]
                cls.add(
                    graph, part_subject, OKH.alternativeLicense,
                    alt_license)  # FIXME: should be the license ID not the reference url, but it breaks the frontend
            cls.add(graph, part_subject, OKH.licensor, get_fallback(part, "licensor"))
            cls.add(graph, part_subject, OKH.material, part.material)
            cls.add(graph, part_subject, OKH.manufacturingProcess, part.manufacturing_process)

            if part.mass:
                cls.add(graph, part_subject, OKH.hasMass, part.mass, rdflib.XSD.float)

            if part.outer_dimensions is not None:
                outer_dimensions = namespace[f"{part_name}_OuterDimensions"]
                cls.add(graph, part_subject, OKH.hasOuterDimensions, outer_dimensions)
                cls.add(graph, outer_dimensions, rdflib.RDF.type, OKH.Dimensions)
                cls.add(graph, outer_dimensions, rdflib.RDFS.label, f"Outer Dimensions of {part.name}")
                cls.add_outer_dimensions(graph, outer_dimensions, part.outer_dimensions)

            if part.tsdc is not None:
                # TODO Parse TsDCs, and check if part.tsdc is a valid tsdc, but maybe do that earlier in the process, not here, while serializing
                cls.add(graph, part_subject, OKH.tsdc, URIRef(f"{BASE_IRI_TSDC}#{part.tsdc}"))

            # source
            for i, file in enumerate(part.source):
                subj = cls._add_file_info(graph,
                                          namespace,
                                          file,
                                          entity_name=f"{part_name}_source{i + 1}",
                                          parent_name=project.name)
                cls.add(graph, part_subject, OKH.source, subj)

            # export
            for i, file in enumerate(part.export):
                subj = cls._add_file_info(graph,
                                          namespace,
                                          file,
                                          entity_name=f"{part_name}_export{i + 1}",
                                          parent_name=project.name)
                cls.add(graph, part_subject, OKH.export, subj)

            # auxiliary
            for i, file in enumerate(part.auxiliary):
                subj = cls._add_file_info(graph,
                                          namespace,
                                          file,
                                          entity_name=f"{part_name}_auxiliary{i + 1}",
                                          parent_name=project.name)
                cls.add(graph, part_subject, OKH.auxiliary, subj)

            # image
            for i, file in enumerate(part.image):
                subj = cls._add_file_info(graph,
                                          namespace,
                                          file,
                                          entity_name=f"{part_name}_image{i + 1}",
                                          parent_name=project.name,
                                          rdf_type=OKH.Image)
                cls.add(graph, part_subject, OKH.hasImage, subj)

            part_subjects.append(part_subject)

        return part_subjects

    @classmethod
    def _add_project(cls, graph: rdflib.Graph, namespace: rdflib.Namespace, fetch_result: FetchResult,
                     project: Project) -> rdflib.URIRef:
        module_subject = namespace['Project']
        cls.add(graph, module_subject, rdflib.RDF.type, OKH.Module)

        cls.add(graph, module_subject, rdflib.RDFS.label, project.name)
        # NOTE That is not how this works. It would have to link to an RDF subject (by IRI) that represents the same module but un-frozen/non-permanent. IT would likely be in an other file.
        #cls.add(graph, module_subject, OKH.versionOf, project.repo)
        cls.add(graph, module_subject, OKH.repo, project.repo)

        cls.add(graph, module_subject, OKH.repoHost, urlparse(project.repo).hostname)
        cls.add(graph, module_subject, OKH.version, project.version)
        cls.add(graph, module_subject, OKH.release, project.release)
        cls.add(graph, module_subject, OKH.license, project.license.id())
        cls.add(graph, module_subject, OKH.licensor, project.licensor)
        cls.add(graph, module_subject, OKH.organization, project.organization)
        # cls.add(graph, module_subject, OKH.contributorCount, None)  # TODO see if GitHub API can do this

        # graph
        # TODO add(OKH.timestamp, project.timestamp)
        cls.add(graph, module_subject, OKH.documentationLanguage, project.documentation_language)
        cls.add(graph, module_subject, OKH.documentationReadinessLevel, cls._make_ODRL(project))
        cls.add(graph, module_subject, OKH.technologyReadinessLevel, cls._make_OTRL(project))
        cls.add(graph, module_subject, OKH.function, project.function)
        cls.add(graph, module_subject, OKH.cpcPatentClass, project.cpc_patent_class)
        for attestation in project.attestation:
            cls.add(graph, module_subject, OKH.attestation, attestation, datatype=rdflib.XSD.anyURI)
        if project.tsdc is not None:
            # TODO Parse TsDCs, and check if part.tsdc is a valid tsdc, but maybe do that earlier in the process, not here, while serializing
            cls.add(graph, module_subject, OKH.tsdc, URIRef(f"{BASE_IRI_TSDC}#{project.tsdc}"))

        # FIXME: yeah, this is not how this works
        # cls.add(graph, module_subject, OKH.export, [file.path for file in project.export])
        # cls.add(graph, module_subject, OKH.source, [file.path for file in project.source])

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
    #         l.append((module, BASE[keyC], rdflib.Literal(value)))
    #         entity = BASE[keyC]
    #         l.append((entity, rdflib.RDF.type, rdflib.OWL.DatatypeProperty))
    #         l.append((entity, rdflib.RDFS.label, rdflib.Literal(key)))
    #         l.append((entity, rdflib.RDFS.subPropertyOf, OKH.functionalMetadata))
    #     return l

    # def _make_file_list(self, project, key, entity_name, rdf_type, BASE, extra=None):
    #     extra = [] if extra is None else extra
    #     parent_name = f"{project.name} {project.version}"
    #     l = []
    #     value = getattr(project, detailskey(key)) if hasattr(project, detailskey(key)) else None
    #     if value is None:
    #         return None
    #     entity = BASE[entity_name]
    #     l.append((entity, rdflib.RDF.type, rdf_type))
    #     l.append((entity, rdflib.RDFS.label, f"{entity_name} of {parent_name}"))
    #     for a, v in extra:
    #         l.append((entity, a, v))
    #     for k, v in value.items():
    #         l.append((entity, getattr(OKH, k), v))
    #     return entity, l

    @classmethod
    def _add_file_info(cls,
                       graph,
                       namespace: rdflib.Namespace,
                       file: File,
                       entity_name: str,
                       parent_name: str | None,
                       rdf_type: URIRef = OKH.File) -> URIRef:
        subj: URIRef = namespace[entity_name]
        cls.add(graph, subj, rdflib.RDF.type, rdf_type)
        cls.add(graph, subj, rdflib.RDFS.label, f'{entity_name} of {parent_name}' if parent_name else entity_name)
        cls._add_file_link(graph, subj, file)
        return subj

    @classmethod
    def _add_file(cls,
                  graph,
                  namespace: rdflib.Namespace,
                  project: Project,
                  key: str,
                  entity_name: str,
                  rdf_type: URIRef = OKH.File) -> URIRef | None:
        parent_name = f"{project.name} {project.version}"
        file = getattr(project, key) if hasattr(project, key) else None
        if file is None:
            return None

        return cls._add_file_info(graph, namespace, file, entity_name, parent_name, rdf_type)

    @classmethod
    def _make_graph(cls, fetch_result: FetchResult, project: Project) -> rdflib.Graph:
        graph: rdflib.Graph = rdflib.Graph()
        graph.bind("okh", OKH)
        graph.bind("okhkrawl", OKHKRAWL)
        graph.bind("otrl", OTRL)
        graph.bind("tsdc", TSDC)
        # graph.bind("tsdcr", TSDCR)
        graph.bind("rdfs", rdflib.RDFS)
        graph.bind("owl", rdflib.OWL)
        graph.bind("xsd", rdflib.XSD)

        namespace = cls._make_project_namespace(project)
        graph.bind("", namespace)

        # NOTE The data-set is the top of the data tree within a manifest,
        #      similar to an `owl:Ontology` in case of a vocabulary.
        data_set_subj = cls._add_data_set(graph, namespace, fetch_result, project)

        module_subject = cls._add_project(graph, namespace, fetch_result, project)
        cls.add(graph, data_set_subj, rdflib.VOID.rootResource, module_subject)

        readme_subject = cls._add_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="readme",
            entity_name="Readme",
            rdf_type=OKH.File,
        )
        if readme_subject is not None:
            cls.add(graph, module_subject, OKH.hasReadme, readme_subject)

        image_subject = cls._add_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="image",
            entity_name="Image",
            rdf_type=OKH.Image,
        )
        if image_subject is not None:
            cls.add(graph, module_subject, OKH.hasImage, image_subject)

        bom_subject = cls._add_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="bom",
            entity_name="BillOfMaterials",
            rdf_type=OKH.File,
        )
        if bom_subject is not None:
            cls.add(graph, module_subject, OKH.hasBoM, bom_subject)

        manufacturing_instructions_subject = cls._add_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="manufacturing_instructions",
            entity_name="ManufacturingInstructions",
            rdf_type=OKH.File,
        )
        if manufacturing_instructions_subject is not None:
            cls.add(graph, module_subject, OKH.hasManufacturingInstructions, manufacturing_instructions_subject)

        user_manual_subject = cls._add_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="user_manual",
            entity_name="UserManual",
            rdf_type=OKH.File,
        )
        if user_manual_subject is not None:
            cls.add(graph, module_subject, OKH.hasUserManual, user_manual_subject)

        part_subjects = cls._add_part(graph, namespace, project)
        for part_subject in part_subjects:
            cls.add(graph, module_subject, OKH.hasComponent, part_subject)

        return graph
