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
from krawl.util import extract_path

log = get_child_logger("gitlab")

BASE_URL='https://gitlab.com'
DEFAULT_DEV_BRANCHES=['master', 'main', 'dev', 'develop', 'development', 'latest', 'current']

class GitLabFileHandler(FileHandler):

    def __init__(self): #, slug: str, version: str, dev_branch: str):
        # self.slug = slug
        self.slug_parts = 2
        self.def_path_parts = 1
        self.pre_vers_path_parts = self.slug_parts + self.def_path_parts
        # self.version = version
        # self.dev_branch = dev_branch

    def _extract_version(self, proj_info: dict, url: str) -> str:
        url_path = extract_path(url)
        path_parts = Path(url_path).relative_to("/").parts
        # log.warning('XXX Reconcatenated path parts: "%s"', '#'.join(path_parts))
        if len(path_parts) <= self.pre_vers_path_parts:
            log.error("Invalid file path in URL for this platform; too few parts: '%s'", url)
            return None
        return path_parts[self.pre_vers_path_parts]

    def gen_proj_info_raw(self, slug: str, version: str, dev_branch: str) -> dict:
        proj_info = {}
        proj_info['slug'] = slug
        proj_info['version'] = version
        proj_info['dev_branch'] = dev_branch
        return proj_info

    def _extract_slug(self, url: str) -> str:
        url_path = extract_path(url)
        path_parts = Path(url_path).relative_to("/").parts
        slug = '/'.join(path_parts[:self.slug_parts])
        # log.warning('XXX Extracted slug is: "%s"', slug)
        return slug

    def gen_proj_info(self, manifest_raw: dict) -> dict:
        repo_url = manifest_raw.get("repo")
        log.debug('XXX repo_url type: "%s"', type(repo_url))
        slug = self._extract_slug(repo_url)
        version = manifest_raw.get("version")
        dev_branch = None # TODO Maybe try to extract this from a files URL, if URLs are used ...
        return self.gen_proj_info_raw(slug, version, dev_branch)

    def _is_dev_branch(self, proj_info: dict, version: str) -> bool:
        extracted_dev_branch = proj_info['dev_branch']
        if extracted_dev_branch is not None:
            return version == extracted_dev_branch
        else:
            return version in DEFAULT_DEV_BRANCHES

    def is_frozen_url(self, proj_info: dict, url: str) -> bool:
        version = self._extract_version(proj_info, url)
        # log.warning('XXX Extracted version is: "%s"', version)
        return not self._is_dev_branch(proj_info, version)

    def to_url(self, proj_info: dict, relative_path: str, frozen: bool) -> str:
        return '{base}/{slug}/raw/{version}/{path}'.format(
            base=BASE_URL,
            slug=proj_info['slug'],
            version=proj_info['version'],
            path=relative_path)

    def extract_path(self, proj_info: dict, url: str) -> bostrol:
        url_path = extract_path(url)
        path_parts = Path(url_path).relative_to("/").parts
        return '/'.join(path_parts[self.pre_vers_path_parts:])
