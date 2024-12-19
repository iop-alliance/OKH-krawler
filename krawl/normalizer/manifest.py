from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import validators

from krawl import dict_utils
from krawl.errors import ParserError
from krawl.fetcher.util import convert_okh_v1_to_losh
from krawl.licenses import get_by_id_or_name as get_license
from krawl.log import get_child_logger
from krawl.normalizer import FileHandler, Normalizer
from krawl.platform_url import PlatformURL
from krawl.project import (File, Mass, Meta, OuterDimensions, OuterDimensionsOpenScad, Part, Project, Software,
                           UploadMethods)
from krawl.util import extract_path as krawl_util_extract_path
from krawl.util import is_url

log = get_child_logger("manifest")


class ManifestNormalizer(Normalizer):

    def __init__(self, file_handler: FileHandler = None):
        self.file_handler = file_handler

    def normalize(self, raw: dict) -> Project:
        project = Project()
        meta = raw.get("meta")
        okhv = raw.get("okhv", None)
        if okhv is None:
            # We assume it is OKH v1
            raw = convert_okh_v1_to_losh(raw)
        if meta is None:
            meta = raw.get("__meta")
        if isinstance(meta, dict):
            project.meta.source = dict_utils.to_string(meta.get("fetcher"))
            if project.meta.source is None:
                project.meta.source = dict_utils.to_string(meta.get("source"))
            project.meta.owner = dict_utils.to_string(meta.get("owner"))
            project.meta.repo = dict_utils.to_string(meta.get("repo"))
            project.meta.path = dict_utils.to_string(meta.get("path"))
            project.meta.branch = dict_utils.to_string(meta.get("branch"))
            # project.meta.created_at = ??? # TODO
            project.meta.last_visited = dict_utils.to_string(meta.get("last_visited"))
            # project.meta.last_changed = ??? # TODO
            log.debug("normalizing manifest of '%s'", project.id)
        else:
            log.debug("normalizing manifest")

        download_url = self._base_url(raw, project.meta)

        fh_proj_info: dict = None
        if self.file_handler is not None:
            fh_proj_info = self.file_handler.gen_proj_info(raw)

        project.name = dict_utils.to_string(raw.get("name"))
        project.repo = dict_utils.to_string(raw.get("repo"))
        project.version = dict_utils.to_string(raw.get("version"))
        project.release = dict_utils.to_string(raw.get("release"))
        project.license = get_license(dict_utils.to_string(raw.get("license")))
        project.licensor = dict_utils.to_string(raw.get("licensor"))
        project.organization = dict_utils.to_string(raw.get("organization"))
        project.readme = self._file(self.file_handler, fh_proj_info, raw.get("readme"), project.meta.path, download_url)
        project.contribution_guide = self._file(self.file_handler, fh_proj_info, raw.get("contribution-guide"),
                                                project.meta.path, download_url)
        project.image = self._file(self.file_handler, fh_proj_info, raw.get("image"), project.meta.path, download_url)
        project.function = dict_utils.to_string(raw.get("function"))
        project.documentation_language = self._language(raw.get("documentation-language"))
        project.technology_readiness_level = dict_utils.to_string(raw.get("technology-readiness-level"))
        project.documentation_readiness_level = dict_utils.to_string(raw.get("documentation-readiness-level"))
        project.attestation = dict_utils.to_string(raw.get("attestation"))
        project.publication = dict_utils.to_string(raw.get("publication"))
        project.standard_compliance = dict_utils.to_string(raw.get("standard-compliance"))
        project.cpc_patent_class = dict_utils.to_string(raw.get("cpc-patent-class"))
        project.tsdc = dict_utils.to_string(raw.get("tsdc"))
        project.bom = self._file(self.file_handler, fh_proj_info, raw.get("bom"), project.meta.path, download_url)
        project.manufacturing_instructions = self._file(self.file_handler, fh_proj_info,
                                                        raw.get("manufacturing-instructions"), project.meta.path,
                                                        download_url)
        project.user_manual = self._file(self.file_handler, fh_proj_info, raw.get("user-manual"), project.meta.path,
                                         download_url)
        project.part = self._parts(self.file_handler, fh_proj_info, raw.get("part"), project.meta.path, download_url)
        project.software = self._software(self.file_handler, fh_proj_info, raw.get("software"), project.meta.path,
                                          download_url)
        project.upload_method = raw.get("upload-method", UploadMethods.MANIFEST)

        return project

    @classmethod
    def _base_url(cls, raw: dict, meta: Meta) -> str:
        # try to use release URL, if exists
        release = dict_utils.to_string(raw.get("release"))
        if release:
            try:
                info = PlatformURL.from_url(release)
                return PlatformURL.as_download_url(info)
            except ValueError:
                pass

        # try to use repo URL and version info
        repo = dict_utils.to_string(raw.get("repo"))
        version = dict_utils.to_string(raw.get("version"))
        if repo and version:
            try:
                platform_url = PlatformURL.from_url(repo)
                platform_url.branch = f"v{version}"
                return PlatformURL.as_download_url(platform_url)
            except ValueError:
                pass

        # try to use meta information
        try:
            platform_url = PlatformURL(
                platform=meta.source,
                owner=meta.owner,
                repo=meta.repo,
                path=meta.path,
                branch=meta.branch,
            )
            return PlatformURL.as_download_url(platform_url)
        except ValueError:
            pass

        return None

    @classmethod
    def _host(cls, raw: dict) -> str | None:
        manifest = raw["manifest"]
        host = dict_utils.to_string(manifest.get("dataHost"))
        if host:
            return host
        repo = dict_utils.to_string(raw.get("repo"))
        if not repo:
            return None
        repo_url = urlparse(repo)
        host = repo_url.netloc.split(":")[0]
        if host:
            return host
        return None

    @classmethod
    def _parts(
            cls,
            file_handler: FileHandler,
            fh_proj_info,
            raw_parts: Any,
            manifest_path: str,
            file_base_url: str) \
            -> list[Part]:
        if raw_parts is None or not isinstance(raw_parts, list):
            return []
        parts = []
        for raw_part in raw_parts:
            part = Part()
            part.name = dict_utils.to_string(raw_part.get("name"))
            part.name_clean = dict_utils.clean_name(part.name)
            part.image = cls._file(file_handler, fh_proj_info, raw_part.get("image"), manifest_path, file_base_url)
            part.source = cls._file(file_handler, fh_proj_info, raw_part.get("source"), manifest_path, file_base_url)
            part.export = cls._files(file_handler, fh_proj_info, raw_part.get("export"), manifest_path, file_base_url)
            part.license = get_license(dict_utils.to_string(raw_part.get("license")))
            part.licensor = dict_utils.to_string(raw_part.get("licensor"))
            part.documentation_language = cls._language(raw_part.get("documentation-language"))
            part.material = dict_utils.to_string(raw_part.get("material"))
            part.manufacturing_process = dict_utils.to_string(raw_part.get("manufacturing-process"))
            part.mass = dict_utils.to_float(raw_part.get("mass"))
            part.outer_dimensions = cls._outer_dimensions(raw_part.get("outer-dimensions"))
            part.tsdc = dict_utils.to_string(raw_part.get("tsdc"))
            parts.append(part)
        dict_utils.ensure_unique_clean_names(parts)
        return parts

    @classmethod
    def _software(cls, file_handler: FileHandler, fh_proj_info: dict, raw_software: Any, manifest_path: str,
                  file_base_url: str) -> list[Part]:
        if raw_software is None or not isinstance(raw_software, list):
            return []
        software = []
        for rs in raw_software:
            s = Software()
            s.release = dict_utils.to_string(rs.get("name"))
            s.installation_guide = cls._file(file_handler, fh_proj_info, rs.get("installation-guide"), manifest_path,
                                             file_base_url)
            s.documentation_language = cls._language(rs.get("documentation-language"))
            s.license = get_license(dict_utils.to_string(rs.get("license")))
            s.licensor = dict_utils.to_string(rs.get("licensor"))
            software.append(s)
        return software

    @classmethod
    def _files(cls, file_handler: FileHandler, fh_proj_info: dict, raw_files: dict, manifest_path: str,
               download_url: str) -> list[File]:
        if raw_files is None or not isinstance(raw_files, list):
            return []
        files = []
        for raw_file in raw_files:
            files.append(cls._file(file_handler, fh_proj_info, raw_file, manifest_path, download_url))
        return files

    @classmethod
    def extract_path(cls, url: str) -> str:
        """Figures out whether the argument is a URL (or a relative path).

        Args:
            url (str): Should represent a hosting platforms URL
        """
        try:
            parsed_url = PlatformURL.from_url(url)
            return parsed_url.path
        except ValueError:
            return krawl_util_extract_path(url)

    @classmethod
    def _pre_parse_file(cls, file_handler: FileHandler, fh_proj_info: dict, raw_file: str, manifest_path: str,
                        download_url: str) -> dict:
        if is_url(raw_file):
            # is URL
            if file_handler is None:
                url = raw_file
                # NOTE We assume, that all platforms we do not support FileHandler for -
                #      i.e. we do not support frozen and non-frozen URLs for -
                #      use (only) non-frozen URLs.
                frozen_url = None
                path = cls.extract_path(url)
            else:
                path = file_handler.extract_path(fh_proj_info, url)
                if file_handler.is_frozen_url(fh_proj_info, url):
                    frozen_url = url
                    url = file_handler.to_url(fh_proj_info, path, False)
                else:
                    frozen_url = file_handler.to_url(fh_proj_info, path, True)
        else:
            # is path relative to/within project/repo
            path = Path(raw_file)
            if path.is_absolute():
                raise ValueError(
                    f"Manifest file path at '{manifest_path}' is absolute, which is invalid!: '{raw_file}'")
            path = str(path)
            if file_handler is None:
                url = f"{download_url}{path}"
                # NOTE Same as above assume, that all platforms we do not support FileHandler for -
                frozen_url = None
            else:
                url = file_handler.to_url(fh_proj_info, path, False)
                frozen_url = file_handler.to_url(fh_proj_info, path, True)
        return {
            "path": path,
            "url": url,
            "frozen-url": frozen_url,
        }

    @classmethod
    def _file(cls, file_handler: FileHandler, fh_proj_info: dict, raw_file: dict, manifest_path: str,
              download_url: str) -> File | None:
        if raw_file is None:
            return None
        if isinstance(raw_file, str):
            try:
                file_dict = cls._pre_parse_file(cls, file_handler, fh_proj_info, raw_file, manifest_path, download_url)
            except ValueError:
                log.error("Failed pre-parsing raw file: {err}")
                return None
        if isinstance(raw_file, dict):
            file_dict = raw_file
        else:
            log.error(f"Unsupported type for file: {type(raw_file)}")
            return None

        file = File()
        file.path = dict_utils.to_path(file_dict.get("path"))
        file.name = str(file.path.with_suffix("")) if file.path and file.path.name else None
        file.mime_type = dict_utils.to_string(file_dict.get("mime-type"))

        url = dict_utils.to_string(file_dict.get("url"))
        if url and validators.url(url):
            file.url = url
        frozen_url = dict_utils.to_string(file_dict.get("frozen-url"))
        if frozen_url and validators.url(frozen_url):
            file.frozen_url = frozen_url

        file.created_at = dict_utils.to_string(file_dict.get("created-at"))
        file.last_changed = dict_utils.to_string(file_dict.get("last-changed"))
        file.last_visited = datetime.now(timezone.utc)
        file.license = get_license(dict_utils.to_string(file_dict.get("license")))
        file.licensor = dict_utils.to_string(file_dict.get("licensor"))

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
