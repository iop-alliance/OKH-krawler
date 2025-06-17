# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from enum import StrEnum
from urllib.parse import urlparse

import validators

from krawl.errors import ParserError


class HostingCategory(StrEnum):
    """The category of hosting platform.
    So far, we only support GitHub like platforms,
    and shove everything else into "Other",
    which so far means: any type of more simple,
    (de)centralized web-hosting."""
    FORGE = "Forge"
    OTHER = "Other"


class HostingType(StrEnum):
    """The type of hosting.
    If it is (de)centralized, this is the used hosting software.
    See also :class:`HostingId`.

    This will likely always be an enum."""
    APPROPEDIA = "Appropedia"
    FORGE_JO = "ForgeJo"
    GIT_HUB = "GitHub"
    GIT_LAB = "GitLab"
    OSHWA = "Oshwa"
    THINGIVERSE = "Thingiverse"
    GIT_REPO = "a_git_repo"
    VARIOUS = "various"

    def __str__(self) -> str:
        match self:
            case self.APPROPEDIA:
                return "SW|appropedia.org"
            case self.FORGE_JO:
                return "SW|forgejo.org"
            case self.GIT_HUB:
                return "SW|github.com"
            case self.GIT_LAB:
                return "SW|gitlab.com"
            case self.OSHWA:
                return "SW|oshwa.org"
            case self.THINGIVERSE:
                return "SW|thingiverse.com"
            case self.VARIOUS:
                return "<UNKNOWN>"
            case _:
                raise NotImplementedError(f"Missing `__str__()` impl for enum variant {self}")

    def category(self) -> HostingCategory:
        match self:
            case self.FORGE_JO | self.GIT_HUB | self.GIT_LAB | self.GIT_REPO:
                return HostingCategory.FORGE
            case self.APPROPEDIA | self.OSHWA | self.THINGIVERSE | self.VARIOUS:
                return HostingCategory.OTHER
            case _:
                raise NotImplementedError(f"Missing `category()` impl for enum variant {self}")


class HostingId(StrEnum):
    """The ID of the hosting.
    If it is (de)centralized, this is the hosting domain.
    See also :class:`HostingType`.

    In the future, this might not be an enum anymore,
    as in the case of distributed hosting technologies,
    the hosting IDs might be many nodes IDs/names."""
    APPROPEDIA_ORG = "appropedia.org"
    CODEBERG_ORG = "codeberg.org"
    GITHUB_COM = "github.com"
    GITLAB_COM = "gitlab.com"
    GITLAB_OPENSOURCEECOLOGY_DE = "gitlab.opensourceecology.de"
    OSHWA_ORG = "oshwa.org"  # "certification.oshwa.org"
    THINGIVERSE_COM = "thingiverse.com"
    MANIFESTS_REPO = "manifests-repo"
    MANIFESTS_LIST_FLAT = "manifests-list-flat"

    def type(self) -> HostingType:
        match self:
            case self.APPROPEDIA_ORG:
                platform_type = HostingType.APPROPEDIA
            case self.CODEBERG_ORG:
                platform_type = HostingType.FORGE_JO
            case self.GITHUB_COM:
                platform_type = HostingType.GIT_HUB
            case self.GITLAB_COM:
                platform_type = HostingType.GIT_LAB
            case self.OSHWA_ORG:
                platform_type = HostingType.OSHWA
            case self.THINGIVERSE_COM:
                platform_type = HostingType.THINGIVERSE
            case self.MANIFESTS_REPO:
                platform_type = HostingType.GIT_REPO
            case self.MANIFESTS_LIST_FLAT:
                platform_type = HostingType.VARIOUS
            case _:
                raise NotImplementedError(f"Missing `self.type()` impl for enum variant {self}")

        return platform_type

    @classmethod
    def from_url(cls, url: str) -> HostingId:
        if not (isinstance(url, str) and validators.url(url)):
            raise ParserError(f"invalid URL '{url}'") from ValueError
        parsed_url = urlparse(url)
        domain = parsed_url.hostname

        match domain:
            case "appropedia.org" | "www.appropedia.org":
                hosting_id = HostingId.APPROPEDIA_ORG
            case "codeberg.org":
                hosting_id = HostingId.CODEBERG_ORG
            case "github.com" | "raw.githubusercontent.com":
                hosting_id = HostingId.GITHUB_COM
            case "gitlab.com":
                hosting_id = HostingId.GITLAB_COM
            case "oshwa.org" | "certification.oshwa.org":
                hosting_id = HostingId.OSHWA_ORG
            case "thingiverse.com" | "www.thingiverse.com":
                hosting_id = HostingId.THINGIVERSE_COM
            case _:
                raise ValueError(f"Unknown platform: '{url}'")

        return hosting_id
