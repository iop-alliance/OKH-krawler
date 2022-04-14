from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import validators

from krawl.licenses import get_by_id_or_name as get_license
from krawl.log import get_child_logger
from krawl.normalizer import Normalizer
from krawl.platform_url import PlatformURL
from krawl.project import File, Mass, Meta, OuterDimensions, Part, Project, Software, UploadMethods

log = get_child_logger("mainfest")


class ManifestNormalizer(Normalizer):

    def normalize(self, raw: dict) -> Project:
        project = Project()
        meta = raw.get("meta")
        if isinstance(meta, dict):
            project.meta.source = self._string(meta.get("fetcher"))
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

        project.name = self._string(raw.get("name"))
        project.repo = self._string(raw.get("repo"))
        project.version = self._string(raw.get("version"))
        project.release = self._string(raw.get("release"))
        project.license = get_license(self._string(raw.get("license")))
        project.licensor = self._string(raw.get("licensor"))
        project.organization = self._string(raw.get("organization"))
        project.readme = self._file(raw.get("readme"), project.meta.path, download_url)
        project.contribution_guide = self._file(raw.get("contribution-guide"), project.meta.path, download_url)
        project.image = self._file(raw.get("image"), project.meta.path, download_url)
        project.function = self._string(raw.get("function"))
        project.documentation_language = self._string(raw.get("documentation-language"))
        project.technology_readiness_level = self._string(raw.get("technology-readiness-level"))
        project.documentation_readiness_level = self._string(raw.get("documentation-readiness-level"))
        project.attestation = self._string(raw.get("attestation"))
        project.publication = self._string(raw.get("publication"))
        project.standard_compliance = self._string(raw.get("standard-compliance"))
        project.cpc_patent_class = self._string(raw.get("cpc-patent-class"))
        project.tsdc = self._string(raw.get("tsdc"))
        project.bom = self._file(raw.get("bom"), project.meta.path, download_url)
        project.manufacturing_instructions = self._file(raw.get("manufacturing-instructions"), project.meta.path,
                                                        download_url)
        project.user_manual = self._file(raw.get("user-manual"), project.meta.path, download_url)
        project.part = self._parts(raw.get("part"), project.meta.path, download_url)
        project.software = self._software(raw.get("software"), project.meta.path, download_url)
        project.upload_method = UploadMethods.MANIFEST

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
    def _parts(cls, raw_parts: Any, manifest_path: str, file_base_url: str) -> list[Part]:
        if raw_parts is None or not isinstance(raw_parts, list):
            return []
        parts = []
        for raw_part in raw_parts:
            part = Part()
            part.name = cls._string(raw_part.get("name"))
            part.image = cls._file(raw_part.get("image"), manifest_path, file_base_url)
            part.source = cls._file(raw_part.get("source"), manifest_path, file_base_url)
            part.export = cls._files(raw_part.get("export"), manifest_path, file_base_url)
            part.license = get_license(cls._string(raw_part.get("license")))
            part.licensor = cls._string(raw_part.get("licensor"))
            part.documentation_language = cls._string(raw_part.get("documentation-language"))
            part.material = cls._string(raw_part.get("material"))
            part.manufacturing_process = cls._string(raw_part.get("manufacturing-process"))
            part.mass = cls._mass(raw_part.get("mass"))
            part.outer_dimensions = cls._outer_dimensions(raw_part.get("outer-dimensions"))
            part.tsdc = cls._string(raw_part.get("tsdc"))
            parts.append(part)
        return parts

    @classmethod
    def _software(cls, raw_software: Any, manifest_path: str, file_base_url: str) -> list[Part]:
        if raw_software is None or not isinstance(raw_software, list):
            return []
        software = []
        for rs in raw_software:
            s = Software()
            s.release = cls._string(rs.get("name"))
            s.installation_guide = cls._file(rs.get("installation-guide"), manifest_path, file_base_url)
            s.documentation_language = cls._string(rs.get("documentation-language"))
            s.license = get_license(cls._string(rs.get("license")))
            s.licensor = cls._string(rs.get("licensor"))
            software.append(s)
        return software

    @classmethod
    def _files(cls, raw_files: dict, manifest_path: str, download_url: str) -> list[File]:
        if raw_files is None or not isinstance(raw_files, list):
            return []
        files = []
        for raw_file in raw_files:
            files.append(cls._file(raw_file, manifest_path, download_url))
        return files

    @classmethod
    def _file(cls, raw_file: dict, manifest_path: str, download_url: str) -> File | None:
        if raw_file is None:
            return None
        if isinstance(raw_file, str):
            # is url
            if validators.url(raw_file):
                try:
                    info = PlatformURL.from_url(raw_file)
                    raw_file = {
                        "path": info.path, # FIXME This should be the repo path, but is the path part of the URL, which in case of git/github, would also contian user- and repo-name (though it may likely not be the same on most other platforms too)
                        "url": raw_file,
                        "perma-url": raw_file,
                    }
                except ValueError:
                    parsed_url = urlparse(raw_file)
                    raw_file = {
                        "path": parsed_url.path, # FIXME This should be the repo path, but is the path part of the URL, which in case of git/github, would also contian user- and repo-name (though it may likely not be the same on most other platforms too)
                        "url": raw_file,
                        "perma-url": raw_file,
                    }
            else:
                # is path within repo
                path = Path(raw_file)
                if path.is_absolute():
                    # path is absolute within repo
                    url = f"{download_url}{str(path)}"
                else:
                    # path is relative to manifest file
                    file_path = path
                    if manifest_path:
                        file_path = Path(manifest_path).parent / file_path
                    file_path = file_path if file_path.is_absolute() else Path("/") / file_path
                    url = f"{download_url}{str(file_path)}"
                raw_file = {
                    "path": path,
                    "url": url,
                    "perma-url": url,
                }
        elif not isinstance(raw_file, dict):
            return None

        file = File()
        file.path = cls._path(raw_file.get("path"))
        file.name = str(file.path.with_suffix("")) if file.path and file.path.name else None
        file.mime_type = cls._string(raw_file.get("mime-type"))

        url = cls._string(raw_file.get("url"))
        if url and validators.url(url):
            file.url = url
        perma_url = cls._string(raw_file.get("perma-url"))
        if perma_url and validators.url(perma_url):
            file.perma_url = perma_url

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
