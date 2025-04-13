# SPDX-FileCopyrightText: 2023 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from pathlib import Path

from krawl.dict_utils import DictUtils
from krawl.errors import NormalizerError
from krawl.log import get_child_logger
from krawl.model.hosting_unit import HostingUnitId
from krawl.normalizer.file_handler import FileHandler
from krawl.util import extract_path

log = get_child_logger("github")

BASE_URL = 'https://github.com'
DEFAULT_DEV_BRANCHES = ['master', 'main', 'dev', 'develop', 'development', 'latest', 'current']


class GitHubFileHandler(FileHandler):

    def __init__(self):  #, slug: str, version: str, dev_branch: str):
        # self.slug = slug
        self.slug_parts = 2
        self.def_path_parts = 1
        self.pre_vers_path_parts = self.slug_parts + self.def_path_parts
        # self.version = version
        # self.dev_branch = dev_branch

    def _extract_version(self, _proj_info: dict, url: str) -> str | None:
        url_path = extract_path(url)
        if not url_path:
            return None
        path_parts = url_path.relative_to("/").parts
        # log.warn('XXX Re-concatenated path parts: "%s"', '#'.join(path_parts))
        if len(path_parts) <= self.pre_vers_path_parts:
            log.error("Invalid file path in URL for this platform; too few parts: '%s'", url)
            return None
        return path_parts[self.pre_vers_path_parts]

    def gen_proj_info_raw(self, slug: str, version: str | None, dev_branch: str | None) -> dict:
        proj_info = {}
        proj_info['slug'] = slug
        if version:
            proj_info['version'] = version
        if dev_branch:
            proj_info['dev_branch'] = dev_branch
        return proj_info

    def _extract_slug(self, url: str) -> str | None:
        if url is None:
            return None
        url_path = extract_path(url)
        if not url_path:
            return None
        path_parts = url_path.relative_to("/").parts
        slug = '/'.join(path_parts[:self.slug_parts])
        # log.warn('XXX Extracted slug is: "%s"', slug)
        return slug

    def gen_proj_info(self, hosting_unit_id: HostingUnitId, manifest_raw: dict) -> dict:
        repo_url = manifest_raw.get("repo")
        if repo_url is None:
            raise NormalizerError("No repo URL in manifest")
        if not isinstance(repo_url, str):
            raise NormalizerError(f"repo URL in manifest should be of type str, but is: {repo_url}")
        slug = self._extract_slug(repo_url)
        if slug is None:
            raise NormalizerError(f"Unable to extract slug from repo URL '{repo_url}'")
        version = DictUtils.to_string(manifest_raw.get("version", "HEAD"))
        dev_branch = None  # TODO Maybe try to extract this from a files URL, if URLs are used ...
        return self.gen_proj_info_raw(slug, version, dev_branch)

    def _is_dev_branch(self, proj_info: dict, version: str) -> bool:
        extracted_dev_branch = proj_info.get('dev_branch')
        if extracted_dev_branch is None:
            return version in DEFAULT_DEV_BRANCHES
        return version == extracted_dev_branch

    def is_frozen_url(self, proj_info: dict, url: str) -> bool:
        version = self._extract_version(proj_info, url)
        if not version:
            return False
        # log.warn('XXX Extracted version is: "%s"', version)
        return not self._is_dev_branch(proj_info, version)

    def is_home_hosting_url(self, proj_info: dict, url: str) -> bool:
        return url.startswith(BASE_URL + '/' + proj_info['slug'] + '/')

    def to_url(self, proj_info: dict, relative_path: str | Path, frozen: bool) -> str:
        base = BASE_URL
        slug = proj_info['slug']
        version = proj_info['version']
        path = relative_path
        return f'{base}/{slug}/raw/{version}/{path}'

    def extract_path(self, proj_info: dict, url: str) -> str:
        url_path = extract_path(url)
        if not url_path:
            return ""
        path_parts = url_path.relative_to("/").parts
        return '/'.join(path_parts[self.pre_vers_path_parts:])
