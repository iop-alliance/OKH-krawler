# SPDX-FileCopyrightText: 2022 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
# SPDX-FileCopyrightText: 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2022 Nicolas Traeder <nicolas@konek.to>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import pathlib
from datetime import datetime, timezone
from typing import Any

from krawl.dict_utils import DictUtils
from krawl.fetcher.result import FetchResult
from krawl.file_formats import get_type_from_extension
from krawl.log import get_child_logger
from krawl.model import licenses
from krawl.model.agent import Person
from krawl.model.file import File, Image
from krawl.model.licenses import LicenseCont
from krawl.model.project import Project
from krawl.normalizer import Normalizer, strip_html
from krawl.shared.thingiverse import BROKEN_IMAGE_URL, LICENSE_MAPPING, Hit, ThingFile, ZipFile
from krawl.util import fix_str_encoding

log = get_child_logger("thingiverse")


class ThingiverseNormalizer(Normalizer):

    def normalize(self, fetch_result: FetchResult) -> Project:
        if not isinstance(fetch_result.data.content, dict):
            raise ValueError(
                f"Thingiverse content expected to be of type dict, but got {type(fetch_result.data.content)}")
        raw: dict[str, Any] = fetch_result.data.content
        # thing: Hit = raw['thing']
        # files: list[ThingFile] = raw['files']
        thing: Hit = raw

        if thing["id"] == 264461:
            thing["description"] = fix_str_encoding(thing["description"])
        # print("$$$$$$$$$$$$$")
        # print(type(things))
        # print("$$$$$$$$$$$$$")
        # print(things)
        # print("$$$$$$$$$$$$$")
        # thing: Hit = things['hits'][0]

        # data_set: DataSet = fetch_result.data_set
        # data_set.hosting_unit_id = data_set.hosting_unit_id.derive(
        #     owner=self._creator(raw),
        #     repo=thing['public_url'],
        # )
        # fetch_result.data_set = data_set

        fetch_result.data_set.crawling_meta.created_at = DictUtils.to_datetime(thing['added'])
        # last_visited = DictUtils.to_datetime(thing["lastVisited"])
        # # last_visited = DictUtils.to_datetime(raw.lastVisited)
        # if last_visited:
        #     # TODO Maybe not a good idea to set this like that?
        #     fetch_result.data_set.crawling_meta.last_visited = last_visited

        if thing['creator']:
            name: str = thing['creator']['first_name'] + ' ' + thing['creator']['last_name']
            creator = Person(name=name.strip(), url=thing['creator']['public_url'])
        else:
            creator = Person(name="ANONYMOUS", url=None)

        # modification_date = dateutil.parser.parse(thing['modified']) if thing['modified'] else None
        # version = str(modification_date.astimezone(timezone.utc)) if modification_date else None
        version = str(thing['modified']) if thing['modified'] else None

        project = Project(name=thing['name'],
                          repo=thing['public_url'],
                          version=version,
                          license=self._license(thing),
                          licensor=[creator])
        project.function = self._function(thing)
        project.documentation_language = self._language_from_description(project.function)
        project.technology_readiness_level = "OTRL-4"
        project.documentation_readiness_level = "ODRL-3"

        project.image = self._images(project, thing)
        project.export = [
            self._file(file) for file in self._filter_files_by_category(thing['zip_data']['files'], "export")
        ]
        project.source = [
            self._file(file) for file in self._filter_files_by_category(thing['zip_data']['files'], "source")
        ]
        return project

    @classmethod
    def _creator(cls, raw_thing):
        if raw_thing['creator']:
            raw_creator = raw_thing["creator"]
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
    def _filter_files_by_category(cls, files: list[ThingFile | ZipFile], category: str) -> list[ThingFile | ZipFile]:
        found_files = []
        for file in files:
            file_format = get_type_from_extension(pathlib.Path(file['name']).suffix)

            if not file_format:
                continue

            if file_format.category == category:
                found_files.append(file)

        return found_files

    @classmethod
    def _license_from_str(cls, tv_license_str: str | None) -> LicenseCont | None:
        if not tv_license_str:
            return None

        if tv_license_str in ('None', 'Other'):
            return None

        mapped_license = LICENSE_MAPPING.get(tv_license_str)

        if not mapped_license:
            return None

        maybe_spdx_id = mapped_license[1]
        return licenses.get_by_id_or_name(maybe_spdx_id)

    # @classmethod
    # def _license_raw(cls, raw: dict) -> LicenseCont:
    #     raw_license = DictUtils.get_key(raw, "license")
    #     return cls._license_from_str(raw_license)

    @classmethod
    def _license(cls, hit: Hit) -> LicenseCont:
        raw_license = hit["license"]
        license_cont = cls._license_from_str(raw_license)
        if not license_cont:
            license_cont = licenses.__unknown_license__
        return license_cont

    @classmethod
    def _function(cls, raw_thing: Hit) -> str | None:
        raw_description = raw_thing.get("description")
        if raw_description:
            return strip_html(raw_description).strip()
        return None

    @classmethod
    def _image(cls, project: Project, images: dict[str, Image], url: str | None, raw: dict) -> None:
        if url and not url == BROKEN_IMAGE_URL:
            file = Image()
            file.path = None
            file.name = raw.get("name", None)
            file.url = url
            file.frozen_url = None
            file.mime_type = file.evaluate_mime_type()
            added_raw = raw.get("added", None)
            if added_raw:
                added_fmtd = datetime.strptime(added_raw, "%Y-%m-%dT%H:%M:%S%z")
                file.created_at = added_fmtd
                file.last_changed = added_fmtd
            file.last_visited = datetime.now(timezone.utc)
            # file.license = project.license
            # file.licensor = project.licensor
            images[url] = file

    @classmethod
    def _images(cls, project: Project, raw_thing: Hit) -> list[Image]:
        images: dict[str, Image] = {}

        thumbnail_url: str | None = raw_thing.get("thumbnail")
        cls._image(project, images, thumbnail_url, raw_thing)

        default_image_raw = raw_thing.get("default_image", None)
        if default_image_raw:
            url: str | None = default_image_raw.get("url")
            cls._image(project, images, url, default_image_raw)

        for img in raw_thing['zip_data']['images']:
            url = img.get("url")
            if url and url not in images:
                cls._image(project, images, url, img)

        return list(images.values())

    @classmethod
    def _file(cls, thing_file: ThingFile | ZipFile) -> File:
        url: str | None = thing_file.get("direct_url")
        if not url:
            url = thing_file.get("url")
        if not url:
            url = thing_file.get("public_url")

        file = File()
        file.path = None
        file.name = thing_file.get("name")
        file.url = url
        file.frozen_url = None
        file.mime_type = file.evaluate_mime_type()
        thing_file_date: str | None = thing_file.get("date")
        file.created_at = datetime.strptime(thing_file_date, "%Y-%m-%d %H:%M:%S") if thing_file_date else None
        file.last_changed = file.created_at
        file.last_visited = datetime.now(timezone.utc)
        # file.license = None
        # file.licensor = None
        return file
