from __future__ import annotations

import logging
import mimetypes
import pathlib
from datetime import datetime, timezone
from pathlib import Path

from langdetect import LangDetectException
from langdetect import detect as detect_language

from krawl import licenses
from krawl.file_formats import get_type_from_extension
from krawl.normalizer import Normalizer, strip_html
from krawl.project import File, Project, UploadMethods

log = logging.getLogger("thingiverse-normalizer")

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
    "Creative Commons - Attribution": "CC-BY-4.0",
    "Creative Commons - Public Domain Dedication": "CC0-1.0",
    "Public Domain": "CC0-1.0",
    "Creative Commons - Attribution - Share Alike": "CC-BY-SA-4.0",
    "GNU - GPL": "GPL-3.0-or-later",
    "GNU - LGPL": "LGPL-3.0-or-later",
    "BSD": "BSD-4-Clause",
    "BSD License": "BSD-4-Clause"
}


class ThingiverseNormalizer(Normalizer):

    def __init__(self):
        mimetypes.init()

    def normalize(self, raw: dict) -> Project | None:
        try:
            project = Project()
            project.meta.source = raw["fetcher"]
            project.meta.owner = self._normalize_creator(raw)
            project.meta.repo = raw['public_url']
            project.meta.created_at = datetime.fromisoformat(raw['added'])
            project.meta.last_visited = raw["lastVisited"]
            project.name = raw['name']
            project.repo = raw['public_url']
            project.version = "1.0.0"
            project.license = self._normalize_license(raw)
            project.licensor = self._normalize_creator(raw)
            project.function = self._normalize_function(raw)
            project.documentation_language = self._normalize_language(project.function)
            project.technology_readiness_level = "ortl4"
            project.documentation_readiness_level = "odrl3"
            project.upload_method = UploadMethods.AUTO

            project.image = self._normalize_image(project, raw)
            project.export = [self._normalize_file(project, file) for file in
                              self._filter_files_by_category(raw["files"], "export")]
            project.source = [self._normalize_file(project, file) for file in
                              self._filter_files_by_category(raw["files"], "source")]
            return project
        except Exception as e:
            log.warning(e)

            return None

    @classmethod
    def _normalize_creator(cls, raw):
        if raw['creator']:
            return raw["creator"]["name"]

        return None

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
    def _filter_files_by_category(cls, files, category):
        found_files = []
        for file in files:
            file_format = get_type_from_extension(pathlib.Path(file['name']).suffix)

            if not file_format:
                continue

            if file_format.category == category:
                found_files.append(file)

        return found_files

    @classmethod
    def _normalize_license(cls, raw: dict):
        raw_license = cls._get_key(raw, "license")

        if not raw_license:
            return None

        ## map those license to blocked licnesens
        invalid_licenses = [
            "Creative Commons - Attribution - Non-Commercial - Share Alike",
            "Creative Commons - Attribution - Non-Commercial - No Derivatives",
            "Creative Commons - Attribution - No Derivatives",
            "Creative Commons - Attribution - Non-Commercial",
            "All Rights Reserved",
        ]

        if raw_license in invalid_licenses:
            return None

        if raw_license == "None" or raw_license == "Other":
            return None

        return licenses.get_by_id_or_name(LICENSE_MAPPING.get(raw_license))

    @classmethod
    def _normalize_function(cls, raw: dict):
        raw_description = raw.get("description")
        if not raw_description:
            return ""
        description = strip_html(raw_description).strip()
        return description

    @classmethod
    def _normalize_language(cls, description: str):
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
    def _normalize_image(cls, project: Project, raw: dict) -> File | None:
        image_raw = raw.get("thumbnail", None)
        if not image_raw:
            return None

        file = File()
        file.path = Path(image_raw)
        file.name = file.path.stem if file.path else None
        file.url = image_raw
        file.perma_url = image_raw
        file.created_at = datetime.strptime(raw["added"], "%Y-%m-%dT%H:%M:%S%z")
        file.last_changed = datetime.strptime(raw["added"], "%Y-%m-%dT%H:%M:%S%z")
        file.last_visited = datetime.now(timezone.utc)
        file.license = project.license
        file.licensor = project.licensor
        return file

    @classmethod
    def _normalize_file(cls, project: Project, raw_file: dict) -> File | None:
        if raw_file is None:
            return None

        type = mimetypes.guess_type(raw_file.get("direct_url"))

        file = File()
        file.path = raw_file.get("direct_url")
        file.name = raw_file.get("name")
        file.mime_type = type[0] if type[0] is not None else "text/plain"
        file.url = raw_file.get("public_url")
        file.perma_url = raw_file.get("public_url")
        file.created_at = datetime.strptime(raw_file.get("date"), "%Y-%m-%d %H:%M:%S")
        file.last_changed = datetime.strptime(raw_file.get("date"), "%Y-%m-%d %H:%M:%S")
        file.last_visited = datetime.now(timezone.utc)
        file.license = project.license
        file.licensor = project.licensor
        return file
