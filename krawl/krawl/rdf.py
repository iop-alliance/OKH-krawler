#!/usr/bin/env python
# coding: utf-8
import argparse
from krawl.common import detailskey
import rdflib as r
from pathlib import Path
from urllib.parse import urlparse, urlunparse
import toml
from rdflib import RDFS, OWL, RDF
from krawl.namespaces import OKH, OTLR

graph = r.Graph()

def make_base_ns(m):
    parts = urlparse(m["repo"])
    base = urlunparse(
        components=(
            parts.scheme,
            parts.netloc,
            str(Path(parts.path, m.get("version", ""))),
            "",
            "",
            "",
        )
    )
    return f"{base}/"

def make_OTRL(m):
    v = m.get("open-technology-readiness-level")
    if v is None:
        return None
    else:
        return getattr(OTLR, v)


def titlecase(s):
    parts = s.split(" ")
    capitalized = "".join([p.capitalize() for p in parts])
    alphanum = "".join([l for l in capitalized if l.isalnum()])
    return alphanum


def camelcase(s, cap=False):
    parts = s.split("-")
    withoutdash = "".join([parts[0]] + [p.capitalize() for p in parts[1:]])
    return withoutdash


def make_part_list(manifest):
    l = list()

    def add(e, attribute, value):
        if value is not None:
            if type(value) == str and value.startswith("http"):
                vboxed = r.URIRef(value)
            else:
                vboxed = r.Literal(value)
            l.append((e, attribute, vboxed))

    def get_fallback(part, key):
        if part.get(key) is not None:
            return part.get(key)
        else:
            return manifest.get(key)

    BASE = r.Namespace(make_base_ns(manifest))
    for part in manifest.get("part", []):
        print("PART")
        # part specific
        partname = titlecase(part["name"])
        p = getattr(BASE, partname)
        l.append((p, RDF.type, OKH.Part))
        add(p, RDFS.label, part["name"])
        add(p, OKH.manufacturingProcess, part.get("process"))
        add(p, OKH.material, part.get("material"))
        add(p, OKH.outerDimensionDim, part.get("outer-dimension-dim"))
        add(p, OKH.outerDimension, part.get("outer-dimension"))
        add(p, OKH.tsdcID, part.get("tsdc-id"))

        # fallback to module
        add(p, OKH.spdxLicense, get_fallback(part, "spdx-license"))
        add(p, OKH.licensor, get_fallback(part, "licensor"))
        add(p, OKH.image, get_fallback(part, "image"))
        add(p, OKH.documentationLanguage, get_fallback(part, "documentation-language"))

        # source file
        source_url = part.get("source")
        if source_url is not None:
            source_name = f"{partname}_source"
            source = getattr(BASE, source_name)
            add(p, OKH.source, source)
            add(source, RDF.type, OKH.SourceFile)
            add(source, OKH.fileUrl, source_url)
            add(source, OKH.fileFormat, "")  # TODO parse *.XXX

        export_urls = part.get("export", [])
        for i, export_url in enumerate(export_urls):
            export_name = f"{partname}_export{i+1}"
            export = getattr(BASE, export_name)
            add(p, OKH.export, export)
            add(export, RDF.type, OKH.ExportFile)
            if isinstance(export_url,str):
                add(export, OKH.fileUrl, export_url)
                ext = export_url.split('.')[-1]
                if(ext != export_url):
                    add(export, OKH.fileFormat, ext)
            if isinstance(export_url, dict):
                add(export, OKH.fileUrl, export_url['fileUrl'])
                add(export, OKH.fileFormat, export_url['fileFormat'])

        # export files

    return l


def make_module_list(m):
    l = list()
    BASE = r.Namespace(make_base_ns(m))
    module = getattr(BASE, titlecase(m["name"]))

    def add(attribute, value):
        if value is not None:
            if type(value) == str and value.startswith("http"):
                vboxed = r.URIRef(value)
            else:
                vboxed = r.Literal(value)
            l.append((module, attribute, vboxed))

    l.append((module, RDF.type, OKH.Module))

    add(RDFS.label, m.get("name"))
    add(OKH.versionOf, m.get("repo"))
    add(OKH.repo, m.get("repo"))
    add(OKH.repoHost, m.get("repoHost"))
    add(OKH.dataSource, m.get("dataSource"))
    add(OKH.version, m.get("version"))
    add(
        OKH.release, None
    )  # TODO look for 'release' in toml or if missing check for latest github release
    add(OKH.spdxLicense, m.get("spdx-license"))
    add(OKH.licensor, m.get("licensor"))
    add(OKH.organisation, m.get("organisation "))
    add(OKH.contributorCount, None)  ## TODO see if github api can do this
    add(OKH.timestamp, m.get("timestamp"))
    add(OKH.documentationLanguage, m.get("documentation-language"))
    add(OKH.technologyReadinessLevel, make_OTRL(m))
    add(OKH.function, m.get("function"))
    add(OKH.cpcPatentClass, m.get("cpc-patent-class"))
    add(OKH.tsdcID, m.get("tsdc-id"))
    add(OKH.bom, m.get("bom"))
    add(OKH.outerDimensionDim, m.get("outer-dimension-dim"))
    add(OKH.outerDimension, m.get("outer-dimension"))
    return l, module


def make_functional_metadata_list(module, functional_metadata, BASE):
    l = list()
    for key, value in functional_metadata.items():
        keyC = camelcase(key)
        l.append((module, getattr(BASE, keyC), r.Literal(value)))
        entity = getattr(BASE, keyC)
        l.append((entity, RDF.type, OWL.DatatypeProperty))
        l.append((entity, RDFS.label, r.Literal(key)))
        l.append((entity, RDFS.subPropertyOf, OKH.functionalMetadata))
    return l


def make_file_list(manifest, key, entityname, rdftype, BASE, extra=[]):
    parentname = f"{manifest.get('name')} v{manifest.get('version')}"
    l = list()
    manifest_details = manifest.get(detailskey(key))
    if manifest_details is None:
        return None, []
    entity = getattr(BASE, entityname)
    l.append((entity, RDF.type, rdftype))
    l.append((entity, RDFS.label, box(f"{entityname} of {parentname}")))
    for a, v in extra:
        l.append((entity, a, v))
    for key, value in manifest_details.items():
        l.append((entity, getattr(OKH, key), box(value)))
    return entity, l


def make_manifest_list(manifest, BASE):
    return make_file_list()


def box(value):
    if type(value) == str and value.startswith("http"):
        vboxed = r.URIRef(value)
    else:
        vboxed = r.Literal(value)
    return vboxed


def make_graph(manifest):
    g = r.Graph()
    g.bind("okh", OKH)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)
    g.bind("otlr", OTLR)
    BASE = r.Namespace(make_base_ns(manifest))
    g.bind("", BASE)

    l, module = make_module_list(manifest)
    l.extend(
        make_functional_metadata_list(
            module, manifest.get("functional-metadata", {}), BASE
        )
    )

    manifest_e, manifest_l = make_file_list(
        manifest,
        "manifest-file",
        "ManifestFile",
        OKH.ManifestFile,
        BASE,
        [(OKH.okhv, box(manifest.get("okhv", "")))],
    )
    if manifest_e is not None:
        l.append((module, OKH.hasManifestFile, manifest_e))
    l.extend(manifest_l)

    readme_e, readme_l = make_file_list(
        manifest,
        "readme",
        "Readme",
        OKH.Readme,
        BASE,
    )
    if readme_e is not None:
        l.append((module, OKH.hasReadme, readme_e))
    l.extend(readme_l)

    image_e, image_l = make_file_list(
        manifest,
        "image",
        "Image",
        OKH.Image,
        BASE,
    )
    if image_e is not None:
        l.append((module, OKH.hasImage, image_e))
    l.extend(image_l)

    bom_e, bom_l = make_file_list(
        manifest,
        "bom",
        "BoM",
        OKH.BoM,
        BASE,
    )
    if bom_e is not None:
        l.append((module, OKH.hasBoM, bom_e))
    l.extend(bom_l)

    mi_e, mi_l = make_file_list(
        manifest,
        "manufacturing-instructions",
        "ManufacturingInstructions",
        OKH.ManufacturingInstructions,
        BASE,
    )
    if mi_e is not None:
        l.append((module, OKH.hasManufacturingInstructions, mi_e))

    l.extend(mi_l)

    um_e, um_l = make_file_list(
        manifest,
        "user-manual",
        "UserManual",
        OKH.UserManual,
        BASE,
    )
    if um_e is not None:
        l.append((module, OKH.hasUserManual, um_e))
    l.extend(um_l)
    part_l = make_part_list(manifest)

    allentries = l + part_l
    for triple in allentries:
        g.add(triple)

    return g


def extend(l, v):
    if v is not None:
        l.extend(v)


def print_graph(g):
    print(g.serialize(format="turtle").decode("utf-8"))
    # print(g.serialiddze(format="turtle", base=BASE).decode("utf-8"))


def make_rdf(manifest: dict, outpath: str, raise_errors=False) -> bool:
    try:
        g = make_graph(manifest)
        g.serialize(destination=str(outpath), format="turtle")
        return True
    except Exception as e:
        print(" RDF ERROR: Couldnt make rdf: ")
        if raise_errors == True:
            raise e
        # exc_info = sys.exc_info()
        print(e)
        # traceback.print_exc(exc_info)
        print(" RDF ERROR END")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "files", metavar="files", help="filepaths to process", nargs="+"
    )
    args = parser.parse_args()
    for file in args.files:
        filepath = Path(file)
        print(f"[RDF] converting: {filepath}")
        with open(file, 'r') as f:
            manifest = toml.loads(f.read())
        make_rdf(manifest, filepath.parent/ "rdf.ttl", True)
        print(f"[RDF]    success: {filepath}")
