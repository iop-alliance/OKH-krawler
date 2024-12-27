# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2022 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
# SPDX-FileCopyrightText: 2022 Nicolas Traeder <nicolas@konek.to>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import validators

from krawl.dict_utils import DictUtils
from krawl.errors import ParserError
from krawl.fetcher.result import FetchResult
from krawl.fetcher.util import convert_okh_v1_dict_to_losh
from krawl.log import get_child_logger
from krawl.model.data_set import DataSet
from krawl.model.file import File
from krawl.model.hosting_unit import HostingUnitIdForge
from krawl.model.licenses import get_by_id_or_name as get_license
from krawl.model.outer_dimensions import OuterDimensions, OuterDimensionsOpenScad
from krawl.model.part import Part
from krawl.model.project import Project
from krawl.model.software import Software
from krawl.model.sourcing_procedure import SourcingProcedure
from krawl.normalizer import Normalizer
from krawl.normalizer.file_handler import FileHandler
from krawl.util import extract_path as krawl_util_extract_path
from krawl.util import is_url

log = get_child_logger("manifest")


class ManifestNormalizer(Normalizer):

    def __init__(self, file_handler: FileHandler = None):
        self.file_handler = file_handler
        self.fh_proj_info: dict = None
        self.manifest_path: str = None
        self.file_dl_base_url: str = None

    def normalize(self, fetch_result: FetchResult) -> Project:
        project = Project()
        raw: dict = fetch_result.data.content
        data_set: DataSet = fetch_result.data_set

        okhv = raw.get("okhv", None)
        if okhv is None:
            # We assume it is OKH v1
            raw = convert_okh_v1_dict_to_losh(raw)

        hosting_unit_id, path = self._evaluate_hosting_id(raw, data_set)

        log.debug("normalizing manifest of '%s'", hosting_unit_id)

        self.file_dl_base_url = hosting_unit_id.create_download_url(path)
        self.manifest_path = data_set.crawling_meta.manifest

        if self.file_handler is not None:
            self.fh_proj_info = self.file_handler.gen_proj_info(raw)

        project.name = DictUtils.to_string(raw.get("name"))
        project.repo = DictUtils.to_string(raw.get("repo"))
        project.version = DictUtils.to_string(raw.get("version"))
        project.release = DictUtils.to_string(raw.get("release"))
        project.license = get_license(DictUtils.to_string(raw.get("license")))
        project.licensor = DictUtils.to_string(raw.get("licensor"))
        project.organization = DictUtils.to_string(raw.get("organization"))
        project.readme = self._file(raw.get("readme"))
        project.contribution_guide = self._file(raw.get("contribution-guide"))
        project.image = self._files(raw.get("image"))
        project.function = DictUtils.to_string(raw.get("function"))
        project.documentation_language = self._language(raw.get("documentation-language"))
        project.technology_readiness_level = DictUtils.to_string(raw.get("technology-readiness-level"))
        project.documentation_readiness_level = DictUtils.to_string(raw.get("documentation-readiness-level"))
        project.attestation = DictUtils.to_string(raw.get("attestation"))
        project.publication = DictUtils.to_string(raw.get("publication"))
        project.standard_compliance = DictUtils.to_string(raw.get("standard-compliance"))
        project.cpc_patent_class = DictUtils.to_string(raw.get("cpc-patent-class"))
        project.tsdc = DictUtils.to_string(raw.get("tsdc"))
        project.bom = self._file(raw.get("bom"))
        project.manufacturing_instructions = self._file(raw.get("manufacturing-instructions"))
        project.user_manual = self._file(raw.get("user-manual"))
        project.outer_dimensions = self._outer_dimensions(raw.get("outer-dimensions"))
        project.part = self._parts(raw.get("part"))
        project.software = self._software(raw.get("software"))
        project.sourcing_procedure = raw.get("data-sourcing-procedure", SourcingProcedure.MANIFEST)

        return project

    @classmethod
    def _evaluate_hosting_id(cls, raw: dict, data_set: DataSet) -> (HostingUnitIdForge, Path):
        # try to use release URL, if exists
        release_url = DictUtils.to_string(raw.get("release"))
        if release_url:
            try:
                return HostingUnitIdForge.from_url(release_url)
            except ParserError:
                pass

        # try to use repo URL and version info
        repo_url = DictUtils.to_string(raw.get("repo"))
        version = DictUtils.to_string(raw.get("version"))
        if repo_url and version:
            try:
                hosting_unit_id = HostingUnitIdForge.from_url_no_path(repo_url)
                # hosting_id.ref = f"v{version}"
                hosting_unit_id = hosting_unit_id.derive(ref=version)
                return hosting_unit_id, None
            except ValueError:
                pass

        # # try to use meta information
        # try:
        #     hosting_unit_id = HostingUnitIdForge(
        #         # platform=meta.source,
        #         owner=meta.owner,
        #         repo=meta.repo,
        #         path=meta.path,
        #         branch=meta.branch,
        #     )
        #     return hosting_unit_id, path
        # except ValueError:
        #     pass

        return None

    @classmethod
    def _host(cls, raw: dict) -> str | None:
        manifest = raw["manifest"]
        host = DictUtils.to_string(manifest.get("dataHost"))
        if host:
            return host
        repo = DictUtils.to_string(raw.get("repo"))
        if not repo:
            return None
        repo_url = urlparse(repo)
        host = repo_url.netloc.split(":")[0]
        if host:
            return host
        return None

    def _parts(self, raw_parts: Any) -> list[Part]:
        if raw_parts is None or not isinstance(raw_parts, list):
            return []
        parts = []
        for raw_part in raw_parts:
            part = Part()
            part.name = DictUtils.to_string(raw_part.get("name"))
            part.name_clean = DictUtils.clean_name(part.name)
            part.image = self._file(raw_part.get("image"))
            part.source = self._file(raw_part.get("source"))
            part.export = self._files(raw_part.get("export"))
            part.license = get_license(DictUtils.to_string(raw_part.get("license")))
            part.licensor = DictUtils.to_string(raw_part.get("licensor"))
            part.documentation_language = self._language(raw_part.get("documentation-language"))
            part.material = DictUtils.to_string(raw_part.get("material"))
            part.manufacturing_process = DictUtils.to_string(raw_part.get("manufacturing-process"))
            part.mass = DictUtils.to_float(raw_part.get("mass"))
            part.outer_dimensions = self._outer_dimensions(raw_part.get("outer-dimensions"))
            part.tsdc = DictUtils.to_string(raw_part.get("tsdc"))
            parts.append(part)
        DictUtils.ensure_unique_clean_names(parts)
        return parts

    def _software(self, raw_software: Any) -> list[Part]:
        if raw_software is None or not isinstance(raw_software, list):
            return []
        software = []
        for rs in raw_software:
            s = Software()
            s.release = DictUtils.to_string(rs.get("name"))
            s.installation_guide = self._file(rs.get("installation-guide"))
            s.documentation_language = self._language(rs.get("documentation-language"))
            s.license = get_license(DictUtils.to_string(rs.get("license")))
            s.licensor = DictUtils.to_string(rs.get("licensor"))
            software.append(s)
        return software

    def _files(self, raw_files: dict) -> list[File]:
        if raw_files is None or not isinstance(raw_files, list):
            return []
        files = []
        for raw_file in raw_files:
            files.append(self._file(raw_file))
        return files

    @classmethod
    def extract_path(cls, url: str) -> str:
        """Figures out whether the argument is a URL (or a relative path).

        Args:
            url (str): Should represent a hosting platforms URL
        """
        try:
            _hosting_id, path = HostingUnitIdForge.from_url(url)
            return path
        except ValueError:
            return krawl_util_extract_path(url)

    def _pre_parse_file(self, raw_file: str) -> dict:
        if is_url(raw_file):
            # is URL
            if self.file_handler is None:
                url = raw_file
                # NOTE We assume, that all platforms we do not support FileHandler for -
                #      i.e. we do not support frozen and non-frozen URLs for -
                #      use (only) non-frozen URLs.
                frozen_url = None
                path = self.extract_path(url)
            else:
                path = self.file_handler.extract_path(self.fh_proj_info, url)
                if self.file_handler.is_frozen_url(self.fh_proj_info, url):
                    frozen_url = url
                    url = self.file_handler.to_url(self.fh_proj_info, path, False)
                else:
                    frozen_url = self.file_handler.to_url(self.fh_proj_info, path, True)
        else:
            # is path relative to/within project/repo
            path = Path(raw_file)
            if path.is_absolute():
                raise ValueError(
                    f"Manifest file path at '{self.manifest_path}' is absolute, which is invalid!: '{raw_file}'")
            path = str(path)
            if self.file_handler is None:
                url = f"{self.file_dl_base_url}{path}"
                # NOTE Same as above assume, that all platforms we do not support FileHandler for -
                frozen_url = None
            else:
                url = self.file_handler.to_url(self.fh_proj_info, path, False)
                frozen_url = self.file_handler.to_url(self.fh_proj_info, path, True)
        return { # TODO Make this a class (or use an existing one, if we already have it)
            "path": path,
            "url": url,
            "frozen-url": frozen_url,
        }

    def _file(self, raw_file: dict) -> File | None:
        if raw_file is None:
            return None

        if isinstance(raw_file, str):
            try:
                file_dict = self._pre_parse_file(raw_file)
            except ValueError as err:
                log.error(f"Failed pre-parsing raw file: {err}")
                return None
        elif isinstance(raw_file, dict):
            file_dict = raw_file
        else:
            raise TypeError(f"Unsupported type for file: {type(raw_file)}")

        file = File()
        file.path = DictUtils.to_path(file_dict.get("path"))
        # pth = file_dict.get("path")
        # log.debug(f"pth: {type(pth)} - '{pth}'")
        # log.debug(f"type(DictUtils.to_path): {type(DictUtils.to_path)}")
        # log.debug(f"type(DictUtils.to_path): {type(DictUtils.to_path)} - '{DictUtils.to_path}'")
        # log.debug(f"type(DictUtils.to_path_ZZZ): {type(DictUtils.to_path)}")
        # log.debug(f"type(DictUtils.clean_name): {type(DictUtils.clean_name)}")
        # import sys
        # sys.exit(99)
        # file.path = DictUtils.to_path(pth)
        file.name = str(file.path.with_suffix("")) if file.path and file.path.name else None
        file.mime_type = DictUtils.to_string(file_dict.get("mime-type"))

        url = DictUtils.to_string(file_dict.get("url"))
        if url and validators.url(url):
            file.url = url
        frozen_url = DictUtils.to_string(file_dict.get("frozen-url"))
        if frozen_url and validators.url(frozen_url):
            file.frozen_url = frozen_url

        file.created_at = DictUtils.to_string(file_dict.get("created-at"))
        file.last_changed = DictUtils.to_string(file_dict.get("last-changed"))
        file.last_visited = datetime.now(timezone.utc)
        file.license = get_license(DictUtils.to_string(file_dict.get("license")))
        file.licensor = DictUtils.to_string(file_dict.get("licensor"))

        return file

    @classmethod
    def _outer_dimensions(cls, raw_outer_dimensions: Any) -> OuterDimensions | None:
        if not isinstance(raw_outer_dimensions, dict):
            return None
        try:
            return OuterDimensions.from_dict(raw_outer_dimensions)
        except ParserError as err:
            try:
                return OuterDimensions.from_openscad(OuterDimensionsOpenScad.from_dict(raw_outer_dimensions))
            except ParserError:
                raise err
