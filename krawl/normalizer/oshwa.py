# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2022 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
# SPDX-FileCopyrightText: 2022 Nicolas Traeder <nicolas@konek.to>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from krawl.dict_utils import DictUtils
from krawl.fetcher.result import FetchResult
from krawl.log import get_child_logger
from krawl.model import licenses
from krawl.model.data_set import DataSet
from krawl.model.project import Project
from krawl.model.sourcing_procedure import SourcingProcedure
from krawl.normalizer import Normalizer, strip_html

log = get_child_logger("oshwa")

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
CATEGORIES_CPC_UNMAPPABLE = [
    "Agriculture", "Arts", "Education", "Electronics", "Environmental", "IOT", "Manufacturing", "Other", "Science",
    "Tool", "Wearables"
]
CATEGORIES_CPC_MAPPING = {
    "3D Printing": "B33Y",
    "Enclosure": "F16M",
    "Home Connection": "H04W",
    "Robotics": "B25J9/00",
    "Sound": "H04R",
    "Space": "B64G"
}


class OshwaNormalizer(Normalizer):

    def normalize(self, fetch_result: FetchResult) -> Project:
        project = Project()
        raw: dict[str, str | dict[str, str | dict[str, str | dict]]] = fetch_result.data.content
        data_set: DataSet = fetch_result.data_set
        # project.meta.source = meta["id"].hosting_id
        # # project.meta.owner = meta["id"].owner
        # project.meta.repo = meta["id"].repo
        # project.meta.last_visited = meta.get("last_visited")

        log.debug("normalizing project metadata '%s'", data_set.hosting_unit_id)
        log.debug("project metadata '%s'", raw)
        project.name = DictUtils.get_key(raw, "projectName")
        project.repo = self._repo(raw)
        project.version = DictUtils.get_key(raw, "projectVersion", default="1.0.0")
        project.license = self._license(raw)
        project.licensor = DictUtils.get_key(raw, "responsibleParty")

        project.function = self._function(raw)
        project.documentation_language = self._language(project.function)
        project.documentation_readiness_level = "ODRL-3*"
        project.cpc_patent_class = self._classification(raw)
        project.sourcing_procedure = SourcingProcedure.API

        # project.specific_api_data["primaryType"] = DictUtils.get_key(raw, "primaryType")
        # project.specific_api_data["additionalType"] = DictUtils.get_key(raw, "additionalType")
        # project.specific_api_data["hardwareLicense"] = DictUtils.get_key(raw, "hardwareLicense")
        # project.specific_api_data["softwareLicense"] = DictUtils.get_key(raw, "softwareLicense")
        # project.specific_api_data["documentationLicense"] = DictUtils.get_key(raw, "documentationLicense")
        # project.specific_api_data["country"] = DictUtils.get_key(raw, "country")
        # certification_date = DictUtils.get_key(raw, "certificationDate")
        # if certification_date:
        #     project.specific_api_data["certificationDate"] = datetime.strptime(certification_date, "%Y-%m-%dT%H:%M%z")

        return project

    @classmethod
    def _classification(cls, raw: dict[str, str | dict]):
        primary_type: str = str(raw.get("primaryType"))

        if primary_type in CATEGORIES_CPC_UNMAPPABLE:
            additional_type = raw.get("additionalType")
            if additional_type is None:
                return None

            for add_type in additional_type:
                cpc_mapped = CATEGORIES_CPC_MAPPING.get(add_type, None)
                if cpc_mapped is not None:
                    return cpc_mapped
            return None

        return CATEGORIES_CPC_MAPPING.get(primary_type, None)

    @classmethod
    def _organization(cls, raw: dict):
        parent_type = raw["parentContent"]["type"]
        if parent_type == "initiative":
            return raw["parentContent"]["title"]
        return None

    @classmethod
    def _license(cls, raw: dict):
        raw_license = DictUtils.get_key(raw, "hardwareLicense")

        if not raw_license:
            return None

        if raw_license == "Other":
            raw_license = DictUtils.get_key(raw, "documentationLicense")

        if not raw_license or raw_license in ["None", "Other"]:
            return None

        return licenses.get_by_id_or_name(LICENSE_MAPPING.get(raw_license, raw_license))

    @classmethod
    def _function(cls, raw: dict):
        raw_description = raw.get("projectDescription")
        if not raw_description:
            return ""
        description = strip_html(raw_description).strip().replace("\r\n", "\n")
        return description

    @classmethod
    def _repo(cls, raw: dict):
        return f"https://certification.oshwa.org/{raw['oshwaUid'].lower()}.html"
