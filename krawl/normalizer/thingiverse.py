from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from langdetect import LangDetectException
from langdetect import detect as detect_language

import krawl.licenses as licenses
from krawl.normalizer import Normalizer, strip_html
from krawl.project import File, Project

log = logging.getLogger("thingiverse-normalizer")
log.setLevel(logging.DEBUG)

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

# TODO
LICENSE_MAPPING = {
    "Creative Commons - Attribution": "CC-BY-4.0",
    "Creative Commons - Public Domain Dedication": "CC0-1.0",
    "Creative Commons - Attribution - Share Alike": "CC-BY-SA-4.0",
    "GNU - GPL": "GPL-3.0-only",
    "BSD": "BSD-4-Clause"
}



class ThingiverseNormalizer(Normalizer):

    def normalize(self, raw: dict) -> Project:
        try:
            project = Project()
            project.meta.source = raw["fetcher"]
            project.meta.host = raw["fetcher"]
            project.meta.owner = self._normalize_creator(raw)
            project.meta.repo = raw['public_url']
            project.meta.created_at = datetime.fromisoformat(raw['added'])
            project.meta.last_visited = raw["lastVisited"]
            project.name = raw['name']
            project.repo = raw['public_url']
            project.version = "0.1.0"  # TODO data missing
            project.release = None
            project.license = self._normalize_license(raw)
            project.licensor = self._normalize_creator(raw)
            # project.organization = self._normalize_organization(raw)
            # project.readme = self._get_info_file(["README"], files) ## TODO fetch readme from github???
            # project.contribution_guide = self._get_info_file(["CONTRIBUTING"], files)
            project.image = self._normalize_image(raw)
            project.function = self._normalize_function(raw)  # TODO
            project.documentation_language = self._normalize_language(project.function)
            project.technology_readiness_level = None
            project.documentation_readiness_level = None
            project.attestation = None
            project.publication = None
            project.standard_compliance = None
            # project.cpc_patent_class = self._normalize_classification(raw)
            project.tsdc = None
            project.bom = None
            project.manufacturing_instructions = None
            # project.user_manual = self._get_info_file(["USERGUIDE", "USERMANUAL"], files)
            project.outer_dimensions_mm = None
            # project.part = self._normalize_parts(files)
            project.software = []
            return project
        except Exception as e:
            log.warning(e.with_traceback())
            log.debug(raw)
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
    def _normalize_license(cls, raw: dict):
        raw_license = cls._get_key(raw, "license")

        if not raw_license:
            return None

        invalid_licenses = [
            "Creative Commons - Attribution - Non-Commercial - Share Alike",
            "Creative Commons - Attribution - Non-Commercial - No Derivatives",
            "Creative Commons - Attribution - No Derivatives",
            "Creative Commons - Attribution - Non-Commercial",
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
    def _normalize_repo(cls, raw: dict):
        doc_url = raw.get('documentationUrl')

        ## TODO can be none

        if not doc_url:
            return f"https://certification.oshwa.org/{raw['oshwaUid']}.html"

        return doc_url

    @classmethod
    def _normalize_image(cls, raw: dict) -> File:
        image_raw = raw.get("thumbnail", {})
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
        file.license = 'CC BY-SA'  # TODO
        file.licensor = raw['creator']['name']
        return file
