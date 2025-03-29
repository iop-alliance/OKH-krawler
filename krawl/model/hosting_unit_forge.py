# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from krawl.errors import ParserError
from krawl.model.hosting_id import HostingId
from krawl.model.hosting_unit import HostingUnitId
from krawl.model.util import create_url
from krawl.util import path_opt

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

# _sha1_pattern = re.compile(r"^[A-Fa-f0-9]{40}$")


@dataclass(slots=True, frozen=True)
class HostingUnitIdForge(HostingUnitId):
    _hosting_id: HostingId
    owner: str
    """The owning user or organization of the project"""
    repo: str
    """The name of the repo/project"""
    group_hierarchy: str | None = None
    """The path leading up to the repo, if any.
    This is [supported by GitLab](https://docs.gitlab.com/ee/user/group/#group-hierarchy),
    but for example GitHub and ForgeJo (CodeBerg) do not support this."""
    ref: str | None = None
    """Could be a branch, tag or commit"""
    path: Path | None = None
    """The path within the repo, commonly pointing to an OKH manifest file."""

    def to_path_str(self) -> str:
        return f"{self.hosting_id()}/{self.owner}{path_opt(self.group_hierarchy)}/{self.repo}{path_opt(self.ref)}{path_opt(self.path)}"

    def hosting_id(self) -> HostingId:
        return self._hosting_id

    def derive(self,
               hosting_id=None,
               owner=None,
               group_hierarchy=None,
               repo=None,
               ref=None,
               path=None) -> HostingUnitIdForge:
        return self.__class__(
            _hosting_id=hosting_id if hosting_id else self.hosting_id(),
            owner=owner if owner else self.owner,
            group_hierarchy=group_hierarchy if group_hierarchy else self.group_hierarchy,
            repo=repo if repo else self.repo,
            ref=ref if ref else self.ref,
            path=path if path else self.path,
        )

    def __eq__(self, other) -> bool:
        return (self.hosting_id() == other.hosting_id() and self.owner == other.owner and
                self.group_hierarchy == other.group_hierarchy and self.repo == other.repo and self.ref == other.ref and
                self.path == other.path)

    def references_version(self) -> bool:
        return self.ref is not None

    def is_valid(self) -> bool:
        return bool(self.hosting_id()) and bool(self.owner) and bool(self.repo)

    @classmethod
    def from_url(cls, url: str) -> tuple[Self, Path | None]:
        hosting_id = HostingId.from_url(url)
        # if not (isinstance(url, str) and validators.url(url)):
        #     raise ValueError(f"invalid URL '{url}'")
        parsed_url = urlparse(url)
        domain = parsed_url.hostname
        path_parts = Path(parsed_url.path).relative_to("/").parts

        owner: str
        group_hierarchy: str | None = None
        repo: str
        path: Path | None = None
        ref: str | None = None
        # TODO Replace all the following with regex matching (with named capture groups)
        match hosting_id:
            case HostingId.GITHUB_COM | HostingId.CODEBERG_ORG:  # FIXME Codeberg is not handled right here
                if len(path_parts) < 2:
                    raise ParserError(f"Not a valid {hosting_id} project URL: {url}")
                owner = path_parts[0]
                repo = path_parts[1]
                if domain == "raw.githubusercontent.com":
                    ref = path_parts[2] if len(path_parts) >= 3 else None
                    path = Path("/".join(path_parts[3:])) if len(path_parts) > 3 else None
                else:
                    if len(path_parts) >= 4 and path_parts[2] in ["tree", "blob", "raw"]:
                        ref = path_parts[3]
                        if len(path_parts) > 4:
                            path = Path("/".join(path_parts[4:]))
                    elif len(path_parts) > 4 and path_parts[2] == "releases" and path_parts[3] == "tag":
                        ref = path_parts[4]
                    elif len(path_parts) > 3 and path_parts[2] == "commit":
                        ref = path_parts[3]
                    else:
                        path = Path("/".join(path_parts[2:])) if len(path_parts) > 2 else None
                    # else:
                    #     raise NotImplementedError(f"Unknown or invalid path format: '{parsed_url.path}'; for platform {hosting_id}.")

            case HostingId.GITLAB_COM:
                if len(path_parts) < 2:
                    raise ParserError(f"Not a valid {hosting_id} project URL: {url}")
                owner = path_parts[0]
                repo = path_parts[1]
                # FIXME GitLab URL path parsing needs work here. We still need to set group_hierarchy!
                if len(path_parts) >= 5 and path_parts[2] == "-" and path_parts[3] in ["tree", "blob", "raw"]:
                    ref = path_parts[4]
                    if len(path_parts) > 5:
                        path = Path("/".join(path_parts[5:]))
                elif len(path_parts) >= 5 and path_parts[2] == "-" and path_parts[3] in ["commit", "tags"]:
                    ref = path_parts[4]
                # else:
                # TODO

            case HostingId.APPROPEDIA_ORG | HostingId.OSHWA_ORG | HostingId.THINGIVERSE_COM:
                raise ParserError(f"This is not a forge(-like) hosting Id: {hosting_id}."
                                  " Please use HostingUnitIdWebById instead.")
                # owner = "none"
                # repo = f"https://certification.oshwa.org/{path_parts[0]}"
                # path = path_parts[0]

                # owner = "none"
                # repo = "https://www.thingiverse.com/"
                # path = path_parts[0]
            case _:
                raise NotImplementedError(f"Unknown hosting ID '{hosting_id}'")

        hosting_unit_id = cls(
            _hosting_id=hosting_id,
            owner=owner,
            repo=repo,
            group_hierarchy=group_hierarchy,
            ref=ref,
            path=path,
        )

        return (hosting_unit_id, None)

    def create_project_hosting_url(self) -> str:
        self.validate()

        match self.hosting_id():
            case HostingId.GITHUB_COM | HostingId.CODEBERG_ORG:
                # format: https://github.com/{owner}/{repo}/
                match self.hosting_id():
                    case HostingId.GITHUB_COM:
                        url_domain = "github.com"
                    case HostingId.CODEBERG_ORG:
                        url_domain = "codeberg.org"
                url_path = f"/{self.owner}/{self.repo}"

            case HostingId.GITLAB_COM | HostingId.GITLAB_OPENSOURCEECOLOGY_DE:
                # format: https://gitlab.com/{owner}/{groups}/{repo}/
                match self.hosting_id():
                    case HostingId.GITHUB_COM:
                        url_domain = "gitlab.com"
                    case HostingId.GITLAB_OPENSOURCEECOLOGY_DE:
                        url_domain = "gitlab.opensourceecology.de"
                url_path = f"/{self.owner}{path_opt(self.group_hierarchy)}/{self.repo}"

            case HostingId.APPROPEDIA_ORG | HostingId.OSHWA_ORG | HostingId.THINGIVERSE_COM:
                raise NotImplementedError(f"This is not a forge(-like) hosting Id: {self.hosting_id()}."
                                          " Please use HostingUnitIdWebById instead.")

            case _:
                raise ValueError(f"Unknown hosting ID '{self.hosting_id()}'")

        return create_url(
            domain=url_domain,
            path=url_path,
        )

    def create_download_url(self, path: Path | str | None) -> str:
        self.validate()

        match self.hosting_id():
            case HostingId.CODEBERG_ORG:
                # format: https://codeberg.org/elevont/ontprox/raw/branch/master/.gitignore
                ref_opt = self.ref if self.ref else "HEAD"
                url_domain = "codeberg.org"
                url_path = f"/{self.owner}/{self.repo}/raw/{ref_opt}{path_opt(path)}"

            case HostingId.GITHUB_COM:
                # format: https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}
                # self.check_is_versioned()
                ref_opt = self.ref if self.ref else "HEAD"
                url_domain = "raw.githubusercontent.com"
                url_path = f"/{self.owner}/{self.repo}/{ref_opt}{path_opt(path)}"

            case HostingId.GITLAB_COM | HostingId.GITLAB_OPENSOURCEECOLOGY_DE:
                # format: https://gitlab.com/{owner}/{groups}/{repo}/-/raw/{branch}/{path}
                # self.check_is_versioned()
                ref_opt = self.ref if self.ref else "HEAD"
                match self.hosting_id():
                    case HostingId.GITLAB_COM:
                        url_domain = "gitlab.com"
                    case HostingId.GITLAB_OPENSOURCEECOLOGY_DE:
                        url_domain = "gitlab.opensourceecology.de"
                    case _:
                        raise NotImplementedError(f"Unhandled hosting ID '{self.hosting_id()}'")
                url_path = f"/{self.owner}/{self.group_hierarchy}/{self.repo}/-/raw/{ref_opt}{path_opt(path)}"

            case HostingId.APPROPEDIA_ORG | HostingId.OSHWA_ORG | HostingId.THINGIVERSE_COM:
                raise NotImplementedError(f"This is not a forge(-like) hosting Id: {self.hosting_id()}."
                                          " Please use HostingUnitIdWebById instead.")

            case _:
                raise ValueError(f"Unknown hosting ID '{self.hosting_id()}'")

        return create_url(
            domain=url_domain,
            path=url_path,
        )
