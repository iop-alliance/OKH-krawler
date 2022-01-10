from __future__ import annotations

import logging
import urllib.parse

from langdetect import LangDetectException
from langdetect import detect as detect_language

import krawl.licenses as licenses
from krawl.normalizer import Normalizer, strip_html
from krawl.project import Project

log = logging.getLogger("oshwa-normalizer")

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


# {
#     "oshwaUid": "SE000004",
#     "responsibleParty": "arturo182",
#     "country": "Sweden",
#     "publicContact": "oledpmod@solder.party",
#     "projectName": "0.95\" OLED PMOD",
#     "projectWebsite": "https://github.com/arturo182/pmod_rgb_oled_0.95in/",
#     "projectVersion": "1.0",
#     "projectDescription": "A tiny color OLED!\r\n\r\nPerfect solution if you need a small display with vivid, high-contrast 16-bit color. PMOD connector can be used with FPGA and MCU dev boards\r\n\r\nThe display itself is a 0.95&quot; color OLED, the resolution is 96x64 RGB pixels.\r\n\r\nThe display is driven by the SSD1331 IC, you can control it with a 4-wire write-only SPI. The board only supports 3.3V logic.",
#     "primaryType": "Other",
#     "additionalType": [
#         "Electronics"
#     ],
#     "projectKeywords": [
#         "oled",
#         "display",
#         "pmod"
#     ],
#     "citations": [],
#     "documentationUrl": "https://github.com/arturo182/pmod_rgb_oled_0.95in/",
#     "hardwareLicense": "CERN",
#     "softwareLicense": "No software",
#     "documentationLicense": "CC BY-SA",
#     "certificationDate": "2020-05-04T00:00-04:00"
# },

class OshwaNormalizer(Normalizer):

    def normalize(self, raw: dict) -> Project:

        project = Project()
        project.meta.source = raw["fetcher"]
        project.meta.host = raw["fetcher"]
        project.meta.owner = raw["responsibleParty"]
        project.meta.repo = self._normalize_repo(raw)
        project.meta.last_visited = raw["lastVisited"]

        log.debug("normalizing '%s'", project.id)
        project.name = raw["projectName"]
        project.repo = self._normalize_repo(raw)
        project.version = urllib.parse.quote(self._get_key(raw, 'projectVersion', default="1.0.0"))
        project.release = ""
        project.license = self._normalize_license(raw)
        project.licensor = raw['responsibleParty']

        project.function = self._normalize_function(raw)
        project.documentation_language = self._normalize_language(project.function)
        project.documentation_readiness_level = "Odrl3Star"
        project.cpc_patent_class = self._normalize_classification(raw)

        project.specific_api_data['test'] = 'SpeificData'
        project.specific_api_data['test2'] = 'SpeificData2'

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
            else:
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
        doc_url = raw.get('documentationUrl')
        if not doc_url:
            return f"https://certification.oshwa.org/{raw['oshwaUid']}.html"
        return doc_url
