from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse

import rdflib
import validators
from rdflib import URIRef

from krawl.errors import SerializerError
from krawl.project import Project
from krawl.serializer import ProjectSerializer

# Useful info about RDF:
# https://medium.com/wallscope/understanding-linked-data-formats-rdf-xml-vs-turtle-vs-n-triples-eb931dbe9827

BASE_IRI_OKH = "https://github.com/OPEN-NEXT/OKH-LOSH/raw/master/OKH-LOSH.ttl"
BASE_IRI_OTRL = "https://github.com/OPEN-NEXT/OKH-LOSH/raw/master/OTRL.ttl"

OKH = rdflib.Namespace(f"{BASE_IRI_OKH}#")
OTRL = rdflib.Namespace(f"{BASE_IRI_OTRL}#")


class RDFProjectSerializer(ProjectSerializer):

    def serialize(self, project: Project) -> str:
        try:
            graph = self._make_graph(project)

            serialized = graph.serialize(format="turtle").decode("utf-8")
        except Exception as err:
            raise SerializerError(f"failed to serialize RDF: {err}") from err
        return serialized

    @staticmethod
    def _make_project_namespace(project) -> rdflib.Namespace:
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
        return otrl_manifest.replace('OTRL-', 'Otrl')

    @staticmethod
    def _make_ODRL(project):
        v = project.documentation_readiness_level
        if v is None:
            return None
        odrl_manifest = getattr(OTRL, v) # NOTE: Yes, ODRL is in the OTRL namespace too!
        return odrl_manifest.replace('ODRL-', 'Odrl').replace('Star', '*')

    @staticmethod
    def _titlecase(s):
        parts = s.split(" ")
        capitalized = "".join([p.capitalize() for p in parts])
        alphanum = "".join([l for l in capitalized if l.isalnum()])
        return alphanum

    @staticmethod
    def _camelcase(s):
        parts = s.split("-")
        withoutdash = "".join([parts[0]] + [p.capitalize() for p in parts[1:]])
        return withoutdash

    @staticmethod
    def add(graph: rdflib.Graph, subject, predicate, object):
        if object is not None:
            if isinstance(object, str) and object.startswith("http") and validators.url(object):
                object = rdflib.URIRef(object)
            elif isinstance(object, datetime):
                object = rdflib.Literal(object.isoformat())
            elif not isinstance(object, (rdflib.URIRef, rdflib.Literal)):
                object = rdflib.Literal(object)
            graph.add((subject, predicate, object))

    @classmethod
    def add_file(cls, graph, subject, file):
        cls.add(graph, subject, OKH.fileUrl, file.url)
        # NOTE This is not part of the spec (as of December 2022), and fileURL is mentioned in the spec to contain the permanent URL; related issue: https://github.com/OPEN-NEXT/OKH-LOSH/issues/132
        # cls.add(graph, subject, OKH.permaURL, file.perma_url)
        cls.add(graph, subject, OKH.fileFormat, file.extension.upper())
        # cls.add(graph, subject, OKH.mimeType, file.mime_type) # FIXME: only add if contained in ontology
        # cls.add(graph, subject, OKH.dateCreated, file.created_at) # FIXME: only add if contained in ontology
        # cls.add(graph, subject, OKH.dateLastChanged, file.last_changed) # FIXME: only add if contained in ontology
        # cls.add(graph, subject, OKH.dateLastVisited, file.last_visited) # FIXME: only add if contained in ontology

    @classmethod
    def add_mass(cls, graph, subject, mass):
        cls.add(graph, subject, OKH.value, mass.value)
        cls.add(graph, subject, OKH.unit, mass.unit)

    @classmethod
    def add_outer_dimensions(cls, graph, subject, outer_dimensions):
        cls.add(graph, subject, OKH.openSCAD, outer_dimensions.openscad)
        cls.add(graph, subject, OKH.unit, outer_dimensions.unit)

    @classmethod
    def _add_part(cls, graph, namespace, project) -> rdflib.URIRef:

        def get_fallback(part, key):
            if hasattr(part, key):
                value = getattr(part, key)
                if value is not None:
                    return value
            return getattr(project, key)

        part_subjects = []
        for part in project.part:
            partname = cls._titlecase(part.name_clean if part.name_clean != project.name else part.name_clean + "_part")

            part_subject = namespace[partname]
            cls.add(graph, part_subject, rdflib.RDF.type, OKH.Part)
            cls.add(graph, part_subject, rdflib.RDFS.label, part.name)

            cls.add(graph, part_subject, OKH.documentationLanguage, get_fallback(part, "documentation_language"))
            license = get_fallback(part, "license")
            if license and license.is_spdx:
                cls.add(graph, part_subject, OKH.spdxLicense, license.reference_url[:-5]
                       )  # FIXME: should be the license ID not the reference url, but it breaks the frontend
            else:
                if license.reference_url is None:
                    alt_license = license.id[:-5]
                else:
                    alt_license = license.reference_url[:-5]
                cls.add(graph, part_subject, OKH.alternativeLicense, alt_license
                       )  # FIXME: should be the license ID not the reference url, but it breaks the frontend
            cls.add(graph, part_subject, OKH.licensor, get_fallback(part, "licensor"))
            cls.add(graph, part_subject, OKH.material, part.material)
            cls.add(graph, part_subject, OKH.manufacturingProcess, part.manufacturing_process)

            if part.mass is not None:
                mass_subject = namespace[f"{partname}_Mass"]
                cls.add(graph, part_subject, OKH.hasMass, mass_subject)
                cls.add(graph, mass_subject, rdflib.RDF.type, OKH.Mass)
                cls.add(graph, mass_subject, rdflib.RDFS.label, f"Mass of {part.name}")
                cls.add_mass(graph, mass_subject, part.mass)

            if part.outer_dimensions is not None:
                outer_dimensions = namespace[f"{partname}_OuterDimensions"]
                cls.add(graph, part_subject, OKH.hasOuterDimensions, outer_dimensions)
                cls.add(graph, outer_dimensions, rdflib.RDF.type, OKH.OuterDimensions)
                cls.add(graph, outer_dimensions, rdflib.RDFS.label, f"Outer Dimensions of {part.name}")
                cls.add_outer_dimensions(graph, outer_dimensions, part.outer_dimensions)

            cls.add(graph, part_subject, OKH.tsdc, part.tsdc)

            # source
            if part.source is not None:
                source_subject = namespace[f"{partname}_source"]
                cls.add(graph, part_subject, OKH.source, source_subject)
                cls.add(graph, source_subject, rdflib.RDF.type, OKH.SourceFile)
                cls.add(graph, source_subject, rdflib.RDFS.label,
                        f"Source File of {part.name} of {project.name} {project.version}")
                cls.add_file(graph, source_subject, part.source)

            # export
            for i, file in enumerate(part.export):
                if file is None:
                    continue
                export_subject = namespace[f"{partname}_export{i + 1}"]
                cls.add(graph, part_subject, OKH.export, export_subject)
                cls.add(graph, export_subject, rdflib.RDF.type, OKH.ExportFile)
                cls.add(graph, export_subject, rdflib.RDFS.label,
                        f"Export File of {part.name} of {project.name} {project.version}")
                cls.add_file(graph, export_subject, file)

            # auxiliary
            for i, file in enumerate(part.auxiliary):
                auxiliary_subject = namespace[f"{partname}_auxiliary{i + 1}"]
                cls.add(graph, part_subject, OKH.auxiliary, auxiliary_subject)
                cls.add(graph, auxiliary_subject, rdflib.RDF.type, OKH.AuxiliaryFile)
                cls.add(graph, auxiliary_subject, rdflib.RDFS.label,
                        f"Auxiliary File of {part.name} of {project.name} {project.version}")
                cls.add_file(graph, auxiliary_subject, file)

            # image
            if part.image is not None:
                image_subject = namespace[f"{partname}_image"]
                cls.add(graph, part_subject, OKH.image, image_subject)
                cls.add(graph, image_subject, rdflib.RDF.type, OKH.Image)
                cls.add(graph, image_subject, rdflib.RDFS.label,
                        f"Image of {part.name} of {project.name} {project.version}")
                cls.add_file(graph, image_subject, part.image)

            part_subjects.append(part_subject)

        return part_subjects

    @classmethod
    def _add_module(cls, graph, namespace, project) -> rdflib.URIRef:
        module_subject = namespace['Project']
        cls.add(graph, module_subject, rdflib.RDF.type, OKH.Module)

        cls.add(graph, module_subject, rdflib.RDFS.label, project.name)
        # NOTE That is not how this works. It would have to link to an RDF subject (by IRI) that represents the same module but un-frozen/non-permanent. IT would likely be in an other file.
        #cls.add(graph, module_subject, OKH.versionOf, project.repo)
        cls.add(graph, module_subject, OKH.repo, project.repo)
        cls.add(graph, module_subject, OKH.dataSource, project.meta.source)

        cls.add(graph, module_subject, OKH.repoHost, urlparse(project.repo).hostname)
        cls.add(graph, module_subject, OKH.version, project.version)
        cls.add(graph, module_subject, OKH.release, project.release)
        if project.license.is_spdx:
            cls.add(graph, module_subject, OKH.spdxLicense, project.license.reference_url[:-5]
                   )  # FIXME: should be the license ID not the reference url, but it breaks the frontend
        else:
            if project.license.reference_url is None:
                alt_license = project.license.id[:-5]
            else:
                alt_license = project.license.reference_url[:-5]
            cls.add(graph, module_subject, OKH.alternativeLicense, alt_license
                   )  # FIXME: should be the license ID not the reference url, but it breaks the frontend
        cls.add(graph, module_subject, OKH.licensor, project.licensor)
        # FIXME: rename organisation to organization, once the frontend is adjusted
        cls.add(graph, module_subject, OKH.organisation, project.organization)
        # cls.add(graph, module_subject, OKH.contributorCount, None)  ## TODO see if github api can do this

        # graph
        # TODO add(OKH.timestamp, project.timestamp)
        cls.add(graph, module_subject, OKH.documentationLanguage, project.documentation_language)
        cls.add(graph, module_subject, OKH.documentationReadinessLevel, cls._make_ODRL(project))
        cls.add(graph, module_subject, OKH.technologyReadinessLevel, cls._make_OTRL(project))
        cls.add(graph, module_subject, OKH.function, project.function)
        cls.add(graph, module_subject, OKH.cpcPatentClass, project.cpc_patent_class)
        cls.add(graph, module_subject, OKH.tsdc, project.tsdc)

        # FIXME: yeah, this is not how this works
        # cls.add(graph, module_subject, OKH.export, [file.path for file in project.export])
        # cls.add(graph, module_subject, OKH.source, [file.path for file in project.source])
        cls.add(graph, module_subject, OKH.uploadMethod, project.upload_method)

        for index in project.specific_api_data:
            cls.add(graph, module_subject,
                    URIRef(f"{BASE_IRI_OKH}#{index}"),
                    project.specific_api_data[index])

        return module_subject

    # def _make_functional_metadata_list(self, module, functional_metadata, BASE):
    #     l = []
    #     for key, value in functional_metadata.items():
    #         keyC = self._camelcase(key)
    #         l.append((module, BASE[keyC], rdflib.Literal(value)))
    #         entity = BASE[keyC]
    #         l.append((entity, rdflib.RDF.type, rdflib.OWL.DatatypeProperty))
    #         l.append((entity, rdflib.RDFS.label, rdflib.Literal(key)))
    #         l.append((entity, rdflib.RDFS.subPropertyOf, OKH.functionalMetadata))
    #     return l

    # def _make_file_list(self, project, key, entityname, rdftype, BASE, extra=None):
    #     extra = [] if extra is None else extra
    #     parentname = f"{project.name} {project.version}"
    #     l = []
    #     value = getattr(project, detailskey(key)) if hasattr(project, detailskey(key)) else None
    #     if value is None:
    #         return None
    #     entity = BASE[entityname]
    #     l.append((entity, rdflib.RDF.type, rdftype))
    #     l.append((entity, rdflib.RDFS.label, f"{entityname} of {parentname}"))
    #     for a, v in extra:
    #         l.append((entity, a, v))
    #     for k, v in value.items():
    #         l.append((entity, getattr(OKH, k), v))
    #     return entity, l

    @classmethod
    def _add_info_file(cls, graph, namespace, project, key, entityname, rdftype):
        parentname = f"{project.name} {project.version}"
        file = getattr(project, key) if hasattr(project, key) else None
        if file is None:
            return None

        subject = namespace[entityname]
        cls.add(graph, subject, rdflib.RDF.type, rdftype)
        cls.add(graph, subject, rdflib.RDFS.label, f"{entityname} of {parentname}")
        cls.add_file(graph, subject, file)
        return subject

    @classmethod
    def _make_graph(cls, project):
        graph = rdflib.Graph()
        graph.bind("okh", OKH)
        graph.bind("otrl", OTRL)
        graph.bind("rdfs", rdflib.RDFS)
        graph.bind("owl", rdflib.OWL)

        namespace = cls._make_project_namespace(project)
        graph.bind("", namespace)

        module_subject = cls._add_module(graph, namespace, project)

        readme_subject = cls._add_info_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="readme",
            entityname="Readme",
            rdftype=OKH.Readme,
        )
        if readme_subject is not None:
            cls.add(graph, module_subject, OKH.hasReadme, readme_subject)

        manifest_file_subject = cls._add_info_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="manifest_file",
            entityname="ManifestFile",
            rdftype=OKH.ManifestFile,
        )
        if manifest_file_subject is not None:
            cls.add(graph, manifest_file_subject, OKH.okhv, project.okhv)
            cls.add(graph, module_subject, OKH.hasManifestFile, manifest_file_subject)

        image_subject = cls._add_info_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="image",
            entityname="Image",
            rdftype=OKH.Image,
        )
        if image_subject is not None:
            cls.add(graph, module_subject, OKH.hasImage, image_subject)

        bom_subject = cls._add_info_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="bom",
            entityname="BillOfMaterials",
            rdftype=OKH.BoM,
        )
        if bom_subject is not None:
            cls.add(graph, module_subject, OKH.hasBoM, bom_subject)

        manufacturing_instructions_subject = cls._add_info_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="manufacturing_instructions",
            entityname="ManufacturingInstructions",
            rdftype=OKH.ManufacturingInstructions,
        )
        if manufacturing_instructions_subject is not None:
            cls.add(graph, module_subject, OKH.hasManufacturingInstructions, manufacturing_instructions_subject)

        user_manual_subject = cls._add_info_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="user_manual",
            entityname="UserManual",
            rdftype=OKH.UserManual,
        )
        if user_manual_subject is not None:
            cls.add(graph, module_subject, OKH.hasUserManual, user_manual_subject)

        part_subjects = cls._add_part(graph, namespace, project)
        for part_subject in part_subjects:
            cls.add(graph, module_subject, OKH.hasComponent, part_subject)

        return graph

    @staticmethod
    def _extend(l, v):
        if v is not None:
            l.extend(v)
