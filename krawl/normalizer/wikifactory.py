from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from langdetect import LangDetectException
from langdetect import detect as detect_language

import krawl.licenses as licenses
from krawl.file_formats import get_formats
from krawl.normalizer import Normalizer, strip_html
from krawl.project import File, Part, Project

log = logging.getLogger("wikifactory-normalizer")

# see https://soulaimanghanem.medium.com/github-repository-structure-best-practices-248e6effc405
EXCLUDE_FILES = [
    "ACKNOWLEDGMENTS",
    "AUTHORS",
    "CHANGELOG",
    "CODE_OF_CONDUCT",
    "CODEOWNERS",
    "CONTRIBUTING",
    "CONTRIBUTORS",
    "FUNDING",
    "ISSUE_TEMPLATE",
    "LICENSE",
    "PULL_REQUEST_TEMPLATE",
    "README",
    "SECURITY",
    "SUPPORT",
    "USERGUIDE",
    "USERMANUAL",
]
LICENSE_MAPPING = {
    "CC-BY-4.0": "CC-BY-4.0",
    "CC0-1.0": "CC0-1.0",
    "MIT": "MIT",
    "BSD-2-Clause": "BSD-2-Clause",
    "CC-BY-SA-4.0": "CC-BY-SA-4.0",
    "GPL-3.0": "GPL-3.0-only",
    "OHL": "TAPR-OHL-1.0",
    "CERN OHL": "CERN-OHL-1.2"
}


class WikifactoryNormalizer(Normalizer):

    def normalize(self, raw: dict) -> Project:
        project = Project()
        meta = raw.get("meta")
        project.meta.source = self._string(meta.get("fetcher"))
        project.meta.owner = self._string(meta.get("owner"))
        project.meta.repo = self._string(meta.get("repo"))
        project.meta.path = self._string(meta.get("path"))
        project.meta.branch = self._string(meta.get("branch"))
        project.meta.created_at = datetime.fromisoformat(raw["dateCreated"])
        project.meta.last_visited = meta.get("last_visited")
        project.meta.last_changed = datetime.fromisoformat(raw["lastUpdated"])

        log.debug("normalizing project metadata '%s'", project.id)
        files = self._get_files(raw)
        project.name = self._string(raw.get("name"))
        project.repo = f"https://wikifactory.com/{raw['parentSlug']}/{raw['slug']}"
        project.version = self._get_key(raw, "contribution", "version")
        project.release = f"https://wikifactory.com/{raw['parentSlug']}/{raw['slug']}/v/{project.version[:7] if project.version else ''}"
        project.license = self._license(raw)
        project.licensor = self._get_key(raw, "creator", "profile", "fullName")
        project.organization = self._organization(raw)
        project.readme = self._get_info_file(["README"], files)
        project.contribution_guide = self._get_info_file(["CONTRIBUTING"], files)
        project.image = self._image(raw)
        project.function = self._function(raw)
        project.documentation_language = self._language(project.function)
        project.technology_readiness_level = None
        project.documentation_readiness_level = None
        project.attestation = None
        project.publication = None
        project.standard_compliance = None
        project.cpc_patent_class = None
        project.tsdc = None
        project.bom = None
        project.manufacturing_instructions = None
        project.user_manual = self._get_info_file(["USERGUIDE", "USERMANUAL"], files)
        project.part = self._parts(files)
        project.software = []

        return project

    @staticmethod
    def _get_key(obj, *key, default=None):
        last = obj
        for k in key:
            if not last or k not in last:
                return default
            last = last[k]
        if not last:
            return default
        return last

    @classmethod
    def _organization(cls, raw: dict):
        parent_type = raw["parentContent"]["type"]
        if parent_type == "initiative":
            return raw["parentContent"]["title"]
        return None

    @classmethod
    def _license(cls, raw: dict):
        raw_license = cls._get_key(raw, "license", "abreviation")  # must be spelled wrong, because it is in the schema
        if not raw_license:
            return None
        license = licenses.get_by_id_or_name(LICENSE_MAPPING.get(raw_license))
        return license

    @classmethod
    def _function(cls, raw: dict):
        raw_description = raw.get("description")
        if not raw_description:
            return ""
        description = strip_html(raw_description).strip()
        return description

    @classmethod
    def _language(cls, description: str):
        if not description:
            return "en"
        try:
            lang = detect_language(description)
        except LangDetectException:
            return "en"
        if lang == "unknown":
            return "en"
        return lang

    @classmethod
    def _file(cls, file_raw: dict) -> File:
        file = File()
        file.path = Path(file_raw["path"]) if "path" in file_raw else \
            Path(file_raw["filename"]) if "filename" in file_raw else None
        file.name = str(file.path.with_suffix("")) if file.path else None
        file.mime_type = file_raw.get("mimeType", None)
        file.url = file_raw.get("url", None)
        file.perma_url = file_raw.get("permalink", None)
        file.created_at = datetime.strptime(file_raw["dateCreated"], "%Y-%m-%dT%H:%M:%S.%f%z")
        file.last_changed = datetime.strptime(file_raw["lastUpdated"], "%Y-%m-%dT%H:%M:%S.%f%z")
        file.last_visited = datetime.now(timezone.utc)
        file.license = file_raw["license"]
        file.licensor = cls._get_key(file_raw, "creator", "profile", "fullName")
        return file

    @classmethod
    def _get_files(cls, raw: dict) -> list[File]:
        raw_files = cls._get_key(raw, "contribution", "files", default=[])
        files = []
        license = cls._license(raw)
        for meta in raw_files:
            file_raw = meta.get("file")
            if not file_raw:
                continue
            dir_name = meta["dirname"]
            if dir_name:
                file_raw["path"] = f"{dir_name}/{file_raw['filename']}"
            file_raw["license"] = license
            file = cls._file(file_raw)
            if file:
                files.append(file)

        return files

    @classmethod
    def _parts(cls, files: list[File]) -> list[Part]:
        # filter out readme and other files
        filtered = []
        for file in files:
            normalized_name = file.path.stem.replace(" ", "_").replace("-", "_").upper()
            if normalized_name in EXCLUDE_FILES:
                continue
            filtered.append(file)

        # put files in buckets
        buckets = defaultdict(list)
        for file in filtered:
            normalized_name = str(file.path.with_suffix("")).lower()
            buckets[normalized_name].append(file)

        # figure out what files are the sources, the exports and the images
        cad_formats = get_formats("cad")
        pcb_formats = get_formats("pcb")
        image_formats = get_formats("image")
        parts = []
        for fl in buckets.values():
            part = Part()
            for file in fl:
                ext = "." + file.extension

                # get sources and exports by extension
                if ext in cad_formats:
                    format_ = cad_formats[ext]
                    if format_.category == "source":
                        if not part.source:
                            part.source = file
                        else:
                            part.export.append(file)
                    elif format_.category == "export":
                        part.export.append(file)
                    continue
                if ext in pcb_formats:
                    format_ = pcb_formats[ext]
                    if format_.category == "source":
                        if not part.source:
                            part.source = file
                        else:
                            part.export.append(file)
                    elif format_.category == "export":
                        part.export.append(file)
                    continue

                # get first image by extension
                if ext in image_formats:
                    format_ = image_formats[ext]
                    if not part.image:
                        part.image = file
                    continue

            # if no sources are identified, but exports, then use the exportsinstead
            if not part.source and part.export:
                part.source = part.export.pop(0)

            # only add, if a source file was identified
            if part.source:
                part.name = part.source.name
                part.license = part.source.license
                part.licensor = part.source.licensor
                parts.append(part)

        return parts

    @classmethod
    def _image(cls, raw: dict) -> File:
        image_raw = raw.get("image", {})
        if not image_raw:
            return None
        return cls._file(image_raw)

    @classmethod
    def _get_info_file(cls, names, files) -> File:
        for file in files:
            # only consider files in root dir
            if len(file.path.parents) > 1:
                continue
            if file.path.stem.strip().replace(" ", "").replace("-", "").replace("_", "").upper() in names:
                return file
        return None
