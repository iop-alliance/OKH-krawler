from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from krawl.licenses import get_by_id_or_name as get_license
from krawl.normalizer import Normalizer
from krawl.project import File, Part, Project

log = logging.getLogger("manifest-normalizer")


class ManifestNormalizer(Normalizer):

    def normalize(self, raw: dict) -> Project:
        project = Project()
        project.meta.source = raw["fetcher"]
        project.meta.host = self._normalize_data_host(raw)
        project.meta.owner = raw["owner"]
        project.meta.repo = raw["repo"]
        project.meta.path = raw["path"]
        # project.meta.created_at = ??? # TODO
        project.meta.last_visited = raw["last_visited"]
        # project.meta.last_changed = ??? # TODO

        log.debug("normalizing '%s'", project.id)
        manifest = raw["manifest"]
        project.name = self._normalize_string(manifest.get("name"))
        project.repo = self._normalize_string(manifest.get("repo"))
        project.version = self._normalize_string(manifest.get("version"))
        project.release = self._normalize_string(manifest.get("release"))
        project.license = get_license(self._normalize_string(manifest.get("license")))
        project.licensor = self._normalize_string(manifest.get("licensor"))
        project.organization = self._normalize_string(manifest.get("organisation"))  # TODO must be renamed
        project.readme = self._normalize_file(manifest.get("readme"))
        project.contribution_guide = self._normalize_file(manifest.get("contribution-guide"))
        project.image = self._normalize_file(manifest.get("image"))
        project.function = self._normalize_string(manifest.get("function"))
        project.documentation_language = self._normalize_string(manifest.get("documentation-language"))
        project.technology_readiness_level = self._normalize_string(manifest.get("technology-readiness-level"))
        project.documentation_readiness_level = self._normalize_string(manifest.get("documentation-readiness-level"))
        project.attestation = self._normalize_string(manifest.get("attestation"))
        project.publication = self._normalize_string(manifest.get("publication"))
        project.standard_compliance = self._normalize_string(manifest.get("standard-compliance"))
        project.cpc_patent_class = self._normalize_string(manifest.get("cpc-patent-class"))
        project.tsdc = self._normalize_string(manifest.get("tsdc"))
        project.bom = self._normalize_file(manifest.get("bom"))
        project.manufacturing_instructions = self._normalize_file(manifest.get("manufacturing-instructions"))
        project.user_manual = self._normalize_file(manifest.get("user-manual"))
        project.outer_dimensions_mm = self._normalize_string(manifest.get("outer-dimensions-mm"))
        project.part = self._normalize_parts(manifest.get("parts"))
        # project.software = self._normalize_software(manifest.get("software")) # TODO

        return project

    @classmethod
    def _normalize_string(cls, value: Any) -> str:
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        if not value:
            return None
        return value

    @classmethod
    def _normalize_data_host(cls, raw: dict) -> str:
        manifest = raw["manifest"]
        host = cls._normalize_string(manifest.get("dataHost"))
        if host:
            return host
        repo = cls._normalize_string(manifest.get("repo"))
        if not repo:
            return None
        repo_url = urlparse(repo)
        host = repo_url.netloc.split(":")[0]
        if host:
            return host
        return None

    @classmethod
    def _normalize_parts(cls, raw_parts: Any) -> list[Part]:
        if raw_parts is None or not isinstance(raw_parts, list):
            return []
        parts = []
        for raw_part in raw_parts:
            part = Part()
            part.name = cls._normalize_string(raw_part.get("name"))
            part.image = cls._normalize_file(raw_part.get("image"))
            part.source = cls._normalize_file(raw_part.get("source"))
            part.export = cls._normalize_files(raw_part.get("export"))
            part.license = get_license(cls._normalize_string(raw_part.get("license")))
            part.licensor = cls._normalize_string(raw_part.get("licensor"))
            part.documentation_language = cls._normalize_string(raw_part.get("documentation_language"))
            part.material = cls._normalize_string(raw_part.get("material"))
            part.manufacturing_process = cls._normalize_string(raw_part.get("manufacturing_process"))
            part.outer_dimensions_mm = cls._normalize_string(raw_part.get("outer_dimensions_mm"))
            part.tsdc = cls._normalize_string(raw_part.get("tsdc"))
            parts.append(part)
        return parts

    @classmethod
    def _normalize_files(cls, raw_files: dict) -> File:
        if raw_files is None or not isinstance(raw_files, list):
            return []
        files = []
        for raw_file in raw_files:
            files.append(cls._normalize_file(raw_file))
        return files

    @classmethod
    def _normalize_file(cls, raw_file: dict) -> File:
        if raw_file is None:
            return None
        if isinstance(raw_file, str):
            raw_file = {"filename": raw_file}
        if not isinstance(raw_file, dict):
            return None
        file = File()
        file.path = Path(raw_file["filename"]) if "filename" in raw_file else None
        file.name = file.path.stem if file.path else None
        file.mime_type = cls._normalize_string(raw_file.get("mime_type"))
        file.url = cls._normalize_string(raw_file.get("url"))
        file.perma_url = cls._normalize_string(raw_file.get("perma_url"))
        file.created_at = cls._normalize_string(raw_file.get("created_at"))
        file.last_changed = cls._normalize_string(raw_file.get("last_changed"))
        file.last_visited = datetime.now(timezone.utc)
        file.license = get_license(cls._normalize_string(raw_file.get("license")))
        file.licensor = cls._normalize_string(raw_file.get("licensor"))
        return file
