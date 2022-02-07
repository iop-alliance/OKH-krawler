from __future__ import annotations

import logging
import urllib.parse
from datetime import datetime

from langdetect import LangDetectException
from langdetect import detect as detect_language

from krawl import licenses
from krawl.normalizer import Normalizer, strip_html
from krawl.project import Project, UploadMethods

log = logging.getLogger("oshwa-normalizer")
log.setLevel(logging.DEBUG)

LICENSE_MAPPING = {
    "CC-BY-4.0": "CC-BY-4.0",
    "CC0-1.0": "CC0-1.0",
    "MIT": "MIT",
    "BSD-2-Clause": "BSD-2-Clause",
    "CC-BY-SA-4.0": "CC-BY-SA-4.0",
    "CC BY-SA": "CC-BY-SA-4.0",
    "GPL-3.0": "GPL-3.0-only",
    "OHL": "TAPR-OHL-1.0",
    "CERN OHL": "CERN-OHL-1.2",
    "CERN": "CERN-OHL-1.2",
}


class OshwaNormalizer(Normalizer):

    def normalize(self, raw: dict) -> Project | None:

        try:
            project = Project()
            project.meta.source = self._get_key(raw, "fetcher")
            project.meta.owner = self._get_key(raw, "responsibleParty")
            project.meta.repo = self._normalize_repo(raw)
            project.meta.last_visited = self._get_key(raw, "lastVisited")

            log.debug("normalizing '%s'", project.id)
            project.name = self._get_key(raw, "projectName")
            project.repo = self._normalize_repo(raw)
            project.version = urllib.parse.quote(self._get_key(raw, 'projectVersion', default="1.0.0"))
            project.license = self._normalize_license(raw)
            project.licensor = self._get_key(raw, 'responsibleParty')

            project.function = self._normalize_function(raw)
            project.documentation_language = self._normalize_language(project.function)
            project.documentation_readiness_level = "Odrl3Star"
            project.cpc_patent_class = self._normalize_classification(raw)
            project.upload_method = UploadMethods.AUTO

            project.specific_api_data['primaryType'] = self._get_key(raw, 'primaryType')
            project.specific_api_data['additionalType'] = self._get_key(raw, 'additionalType')
            project.specific_api_data['hardwareLicense'] = self._get_key(raw, 'hardwareLicense')
            project.specific_api_data['softwareLicense'] = self._get_key(raw, 'softwareLicense')
            project.specific_api_data['documentationLicense'] = self._get_key(raw, 'documentationLicense')
            project.specific_api_data['country'] = self._get_key(raw, 'country')

            certification_date = self._get_key(raw, "certificationDate")
            if certification_date:
                project.specific_api_data['certificationDate'] = datetime.strptime(certification_date,
                                                                                   "%Y-%m-%dT%H:%M%z")
            return project
        except Exception as e:
            log.warning("Raw Oshwa data could not be normalized: %s", e)
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
    def _normalize_classification(cls, raw: dict):
        primary_type = raw.get("primaryType")
        additional_type = raw.get("additionalType")

        unmappable_categories = [
            "Arts",
            "Education",
            "Environmental",
            "Manufacturing",
            "Other",
            "Science",
            "Tool"
        ]

        if primary_type in unmappable_categories:
            if additional_type is None:
                return ""
            if len(additional_type) == 0:
                return ""

            return additional_type

        mapping_primary_to_cpc = {
            "3D Printing": "B33Y",
            "Agriculture": "A01",
            "Electronics": "H",
            "Enclosure": "F16M",
            "Home Connection": "H04W",
            "IOT": "H04",
            "Robotics": "B25J9 / 00",
            "Sound": "H04R",
            "Space": "B64G",
            "Wearables": "H"
        }

        try:
            cpc = mapping_primary_to_cpc[primary_type]
            return cpc
        except KeyError:
            return primary_type

    @classmethod
    def _normalize_organization(cls, raw: dict):
        parent_type = raw["parentContent"]["type"]
        if parent_type == "initiative":
            return raw["parentContent"]["title"]
        return None

    @classmethod
    def _normalize_license(cls, raw: dict):

        raw_license = cls._get_key(raw, "hardwareLicense")

        if not raw_license:
            return None

        if raw_license == "Other":
            raw_license = cls._get_key(raw, "documentationLicense")

        if not raw_license or raw_license == "None" or raw_license == "Other":
            return None

        return licenses.get_by_id_or_name(LICENSE_MAPPING.get(raw_license))

    @classmethod
    def _normalize_function(cls, raw: dict):
        raw_description = raw.get("projectDescription")
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
        return f"https://certification.oshwa.org/{raw['oshwaUid']}.html"
