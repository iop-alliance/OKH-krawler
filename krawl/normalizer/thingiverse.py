# SPDX-FileCopyrightText: 2022 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
# SPDX-FileCopyrightText: 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2022 Nicolas Traeder <nicolas@konek.to>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import mimetypes
import pathlib
from datetime import datetime, timezone
from pathlib import Path

from krawl.dict_utils import DictUtils
from krawl.fetcher.result import FetchResult
from krawl.file_formats import get_type_from_extension
from krawl.log import get_child_logger
from krawl.model import licenses
from krawl.model.data_set import DataSet
from krawl.model.file import File
from krawl.model.project import Project
from krawl.normalizer import Normalizer, strip_html

log = get_child_logger("thingiverse")

# Maps Thingiverse license names to (search_id, SPDX-Id).
# If SPDX-Id is None, the license is not Open Source.
LICENSE_MAPPING = {
    "Creative Commons - Attribution": ("cc", "CC-BY-4.0"),
    "Creative Commons - Attribution - Share Alike": ("cc-sa", "CC-BY-SA-4.0"),
    "Creative Commons - Attribution - No Derivatives": ("cc-nd", None),
    "Creative Commons - Attribution - Non-Commercial": ("cc-nc", None),
    "Creative Commons - Attribution - Non-Commercial - Share Alike": ("cc-nc-sa", None),
    "Creative Commons - Attribution - Non-Commercial - No Derivatives": ("cc-nc-nd", None),
    "Creative Commons - Share Alike": ("cc-sa", "CC-BY-SA-4.0"),
    "Creative Commons - No Derivatives": ("cc-nd", None),
    "Creative Commons - Non-Commercial": ("cc-nc", None),
    "Creative Commons - Non Commercial - Share alike": ("cc-nc-sa", None),
    "Creative Commons - Non Commercial - No Derivatives": ("cc-nc-nd", None),
    "Creative Commons - Public Domain Dedication": ("pd0", "CC0-1.0"),
    "Public Domain": ("public", "CC0-1.0"),
    "GNU - GPL": ("gpl", "GPL-3.0-or-later"),
    "GNU - LGPL": ("lgpl", "LGPL-3.0-or-later"),
    "BSD": ("bsd", "BSD-4-Clause"),
    "BSD License": ("bsd", "BSD-4-Clause"),
    "Nokia": ("nokia", None),
    "All Rights Reserved": ("none", None),
    "Other": (None, None),
    "None": (None, None),
}
BROKEN_IMAGE_URL = 'https://cdn.thingiverse.com/'


class ThingiverseNormalizer(Normalizer):

    def __init__(self):
        mimetypes.init()

    def normalize(self, fetch_result: FetchResult) -> Project:
        raw: dict = fetch_result.data.content
        data_set: DataSet = fetch_result.data_set

        data_set.hosting_unit_id = data_set.hosting_unit_id.derive(
            owner=self._creator(raw),
            repo=raw['public_url'],
        )
        fetch_result.data_set = data_set

        fetch_result.data_set.crawling_meta.created_at = datetime.fromisoformat(raw['added'])
        fetch_result.data_set.crawling_meta.last_visited = raw[
            "lastVisited"]  # TODO Maybe not a good idea to set this like that?
        project = Project(name=raw['name'],
                          repo=raw['public_url'],
                          version=raw['modified'],
                          license=self._license(raw),
                          licensor=data_set.hosting_unit_id.owner)
        project.function = self._function(raw)
        project.documentation_language = self._language(project.function)
        project.technology_readiness_level = "OTRL-4"
        project.documentation_readiness_level = "ODRL-3"

        project.image = self._images(project, raw)
        project.export = [self._file(project, file) for file in self._filter_files_by_category(raw["files"], "export")]
        project.source = [self._file(project, file) for file in self._filter_files_by_category(raw["files"], "source")]
        return project

    @classmethod
    def _creator(cls, raw):
        if raw['creator']:
            raw_creator = raw["creator"]
            creator = {}
            if raw_creator["name"]:
                creator["name"] = raw_creator["name"]
            if raw_creator["public_url"]:
                creator["url"] = raw_creator["public_url"]
            if not creator:
                creator = None
            return creator
        return None

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
    def _license(cls, raw: dict):
        raw_license = DictUtils.get_key(raw, "license")

        if not raw_license:
            return None

        if raw_license in ('None', 'Other'):
            return None

        mapped_license = LICENSE_MAPPING.get(raw_license)

        if not mapped_license:
            return None

        maybe_spdx_id = mapped_license[1]
        return licenses.get_by_id_or_name(maybe_spdx_id)

    @classmethod
    def _function(cls, raw: dict) -> str | None:
        raw_description = raw.get("description")
        if raw_description:
            return strip_html(raw_description).strip()
        return None

    @classmethod
    def _image(cls, project: Project, images: list[File], url: str, raw: dict) -> None:
        if url and not url == BROKEN_IMAGE_URL:
            file = File()
            file.path = Path(url)
            file.name = raw.get("name", None)
            file.url = url
            file.frozen_url = None
            added_raw = raw.get("added", None)
            if added_raw:
                added_fmtd = datetime.strptime(added_raw, "%Y-%m-%dT%H:%M:%S%z")
                file.created_at = added_fmtd
                file.last_changed = added_fmtd
            file.last_visited = datetime.now(timezone.utc)
            file.license = project.license
            file.licensor = project.licensor
            images.append(file)

    @classmethod
    def _images(cls, project: Project, raw: dict) -> list[File]:
        images = []

        thumbnail_url = raw.get("thumbnail", None)
        cls._image(project, images, thumbnail_url, raw)

        default_image_raw = raw.get("default_image", None)
        if default_image_raw:
            url = default_image_raw.get("url", None)
            cls._image(project, images, url, default_image_raw)

        return images

    @classmethod
    def _file(cls, project: Project, raw_file: dict) -> File | None:
        if raw_file is None:
            return None

        type = mimetypes.guess_type(raw_file.get("direct_url"))

        file = File()
        file.path = raw_file.get("direct_url")
        file.name = raw_file.get("name")
        # file.mime_type = type[0] if type[0] is not None else "text/plain"
        file.mime_type = type[0]  # might be None
        file.url = raw_file.get("public_url")
        file.frozen_url = None
        file.created_at = datetime.strptime(raw_file.get("date"), "%Y-%m-%d %H:%M:%S")
        file.last_changed = datetime.strptime(raw_file.get("date"), "%Y-%m-%d %H:%M:%S")
        file.last_visited = datetime.now(timezone.utc)
        file.license = project.license
        file.licensor = project.licensor
        return file
