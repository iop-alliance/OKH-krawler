from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import validators

from krawl.licenses import get_by_id_or_name as get_license
from krawl.log import get_child_logger
from krawl.normalizer import Normalizer, FileHandler
from krawl.platform_url import PlatformURL
from krawl.project import File, Mass, Meta, OuterDimensions, Part, Project, Software, UploadMethods
from krawl.util import is_url

log = get_child_logger("manifest")


class ManifestNormalizer(Normalizer):

    def __init__(self, file_handler: FileHandler = None):
        self.file_handler = file_handler

    def normalize(self, raw: dict) -> Project:
        project = Project()
        meta = raw.get("meta")
        if meta is None:
            meta = raw.get("__meta")
        if isinstance(meta, dict):
            project.meta.source = self._string(meta.get("fetcher"))
            if project.meta.source is None:
                project.meta.source = self._string(meta.get("source"))
            project.meta.owner = self._string(meta.get("owner"))
            project.meta.repo = self._string(meta.get("repo"))
            project.meta.path = self._string(meta.get("path"))
            project.meta.branch = self._string(meta.get("branch"))
            # project.meta.created_at = ??? # TODO
            project.meta.last_visited = self._string(meta.get("last_visited"))
            # project.meta.last_changed = ??? # TODO
            log.debug("normalizing manifest of '%s'", project.id)
        else:
            log.debug("normalizing manifest")

        download_url = self._base_url(raw, project.meta)

        fh_proj_info: dict = None
        if self.file_handler is not None:
            fh_proj_info = self.file_handler.gen_proj_info(raw)

        project.name = self._string(raw.get("name"))
        project.repo = self._string(raw.get("repo"))
        project.version = self._string(raw.get("version"))
        project.release = self._string(raw.get("release"))
        project.license = get_license(self._string(raw.get("license")))
        project.licensor = self._string(raw.get("licensor"))
        project.organization = self._string(raw.get("organization"))
        project.readme = self._file(self.file_handler, fh_proj_info, raw.get("readme"), project.meta.path, download_url)
        project.contribution_guide = self._file(self.file_handler, fh_proj_info, raw.get("contribution-guide"), project.meta.path, download_url)
        project.image = self._file(self.file_handler, fh_proj_info, raw.get("image"), project.meta.path, download_url)
        project.function = self._string(raw.get("function"))
        project.documentation_language = self._string(raw.get("documentation-language"))
        project.technology_readiness_level = self._string(raw.get("technology-readiness-level"))
        project.documentation_readiness_level = self._string(raw.get("documentation-readiness-level"))
        project.attestation = self._string(raw.get("attestation"))
        project.publication = self._string(raw.get("publication"))
        project.standard_compliance = self._string(raw.get("standard-compliance"))
        project.cpc_patent_class = self._string(raw.get("cpc-patent-class"))
        project.tsdc = self._string(raw.get("tsdc"))
        project.bom = self._file(self.file_handler, fh_proj_info, raw.get("bom"), project.meta.path, download_url)
        project.manufacturing_instructions = self._file(self.file_handler, fh_proj_info, raw.get("manufacturing-instructions"), project.meta.path,
                                                        download_url)
        project.user_manual = self._file(self.file_handler, fh_proj_info, raw.get("user-manual"), project.meta.path, download_url)
        project.part = self._parts(self.file_handler, fh_proj_info, raw.get("part"), project.meta.path, download_url)
        project.software = self._software(self.file_handler, fh_proj_info, raw.get("software"), project.meta.path, download_url)
        project.upload_method = raw.get("upload-method", UploadMethods.MANIFEST)

        return project

    @classmethod
    def _base_url(cls, raw: dict, meta: Meta) -> str:
        # try to use release URL, if exists
        release = cls._string(raw.get("release"))
        if release:
            try:
                info = PlatformURL.from_url(release)
                return PlatformURL.as_download_url(info)
            except ValueError:
                pass

        # try to use repo URL and version info
        repo = cls._string(raw.get("repo"))
        version = cls._string(raw.get("version"))
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
        host = cls._string(manifest.get("dataHost"))
        if host:
            return host
        repo = cls._string(raw.get("repo"))
        if not repo:
            return None
        repo_url = urlparse(repo)
        host = repo_url.netloc.split(":")[0]
        if host:
            return host
        return None

    @classmethod
    def _parts(cls, file_handler: FileHandler, fh_proj_info, raw_parts: Any, manifest_path: str, file_base_url: str) -> list[Part]:
        if raw_parts is None or not isinstance(raw_parts, list):
            return []
        parts = []
        for raw_part in raw_parts:
            part = Part()
            part.name = cls._string(raw_part.get("name"))
            part.name_clean = cls._clean_name(part.name)
            part.image = cls._file(file_handler, fh_proj_info, raw_part.get("image"), manifest_path, file_base_url)
            part.source = cls._file(file_handler, fh_proj_info, raw_part.get("source"), manifest_path, file_base_url)
            part.export = cls._files(file_handler, fh_proj_info, raw_part.get("export"), manifest_path, file_base_url)
            part.license = get_license(cls._string(raw_part.get("license")))
            part.licensor = cls._string(raw_part.get("licensor"))
            part.documentation_language = cls._string(raw_part.get("documentation-language"))
            part.material = cls._string(raw_part.get("material"))
            part.manufacturing_process = cls._string(raw_part.get("manufacturing-process"))
            part.mass = cls._mass(raw_part.get("mass"))
            part.outer_dimensions = cls._outer_dimensions(raw_part.get("outer-dimensions"))
            part.tsdc = cls._string(raw_part.get("tsdc"))
            parts.append(part)
        cls._ensure_unique_clean_names(parts)
        return parts

    @classmethod
    def _software(cls, file_handler: FileHandler, fh_proj_info: dict, raw_software: Any, manifest_path: str, file_base_url: str) -> list[Part]:
        if raw_software is None or not isinstance(raw_software, list):
            return []
        software = []
        for rs in raw_software:
            s = Software()
            s.release = cls._string(rs.get("name"))
            s.installation_guide = cls._file(file_handler, fh_proj_info, rs.get("installation-guide"), manifest_path, file_base_url)
            s.documentation_language = cls._string(rs.get("documentation-language"))
            s.license = get_license(cls._string(rs.get("license")))
            s.licensor = cls._string(rs.get("licensor"))
            software.append(s)
        return software

    @classmethod
    def _files(cls, file_handler: FileHandler, fh_proj_info: dict, raw_files: dict, manifest_path: str, download_url: str) -> list[File]:
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
            file_reference (str): Should represent either a URL or a relative path
        """
        try:
            parsed_url = PlatformURL.from_url(url)
            return parsed_url.path
        except ValueError:
            return krawl.util.extract_path(url)

    @classmethod
    def _file(cls, file_handler: FileHandler, fh_proj_info: dict, raw_file: dict, manifest_path: str, download_url: str) -> File | None:
        if raw_file is None:
            return None
        if isinstance(raw_file, str):
            # is URL
            if is_url(raw_file):
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
                raw_file = {
                    "path": path,
                    "url": url,
                    "frozen-url": frozen_url,
                }
            else:
                # is path relative to/within project/repo
                path = Path(raw_file)
                if path.is_absolute():
                    log.error("Manifest file path at '%s' is absolute, which is invalid!: '%s'", manifest_path, raw_file)
                    return None
                path = str(path)
                if file_handler is None:
                    url = f"{download_url}{path}"
                    # NOTE Same as above assume, that all platforms we do not support FileHandler for -
                    frozen_url = None
                else:
                    url = file_handler.to_url(fh_proj_info, path, False)
                    frozen_url = file_handler.to_url(fh_proj_info, path, True)
                raw_file = {
                    "path": path,
                    "url": url,
                    "frozen-url": frozen_url,
                }
        elif not isinstance(raw_file, dict):
            log.error("Manifest file path '%s' is not a string, which is invalid!: '%s'", manifest_path, str(raw_file))
            return None

        file = File()
        file.path = cls._path(raw_file.get("path"))
        file.name = str(file.path.with_suffix("")) if file.path and file.path.name else None
        file.mime_type = cls._string(raw_file.get("mime-type"))

        url = cls._string(raw_file.get("url"))
        if url and validators.url(url):
            file.url = url
        frozen_url = cls._string(raw_file.get("frozen-url"))
        if frozen_url and validators.url(frozen_url):
            file.frozen_url = frozen_url

        file.created_at = cls._string(raw_file.get("created-at"))
        file.last_changed = cls._string(raw_file.get("last-changed"))
        file.last_visited = datetime.now(timezone.utc)
        file.license = get_license(cls._string(raw_file.get("license")))
        file.licensor = cls._string(raw_file.get("licensor"))

        return file

    @classmethod
    def _mass(cls, raw_mass: Any) -> Mass | None:
        if not isinstance(raw_mass, dict):
            return None
        m = Mass()
        m.value = cls._float(raw_mass.get("value"))
        m.unit = cls._string(raw_mass.get("unit"))
        return m

    @classmethod
    def _outer_dimensions(cls, raw_outer_dimensions: Any) -> OuterDimensions | None:
        if not isinstance(raw_outer_dimensions, dict):
            return None
        od = OuterDimensions()
        od.openscad = cls._string(raw_outer_dimensions.get("openSCAD"))
        od.unit = cls._string(raw_outer_dimensions.get("unit"))
        return od
