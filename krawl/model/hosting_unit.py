from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from krawl.errors import ParserError
from krawl.model.hosting_id import HostingId
from krawl.model.util import create_url

# import validators

_sha1_pattern = re.compile(r"^[A-Fa-f0-9]{40}$")

OVERRIDE_MSG = "The sub-class needs to overwrite this method"


@dataclass(slots=True, frozen=True)
class HostingUnitId:
    """A "unit of storage" that holds a single project,
    for example a GitHub repo or an IPFS hash.
    """

    @classmethod
    def from_url_no_path(cls, url: str) -> HostingUnitId:
        id, path = cls.from_url(url)
        if path:
            raise ParserError(f"Project hosting URL should have no path part: '{url}'")
        return id

    @classmethod
    def from_url(cls, url: str) -> (HostingUnitId, Path):
        raise NotImplementedError(OVERRIDE_MSG)

    def to_path_str(self) -> str:
        raise NotImplementedError(OVERRIDE_MSG)

    def __str__(self) -> str:
        return self.to_path_str()

    def to_path(self) -> Path:
        return Path(self.to_path_str())

    def hosting_id(self) -> HostingId:
        raise NotImplementedError(OVERRIDE_MSG)

    def __eq__(self, other) -> bool:
        raise NotImplementedError(OVERRIDE_MSG)

    def references_version(self) -> bool:
        raise NotImplementedError(OVERRIDE_MSG)

    def check_is_versioned(self) -> None:
        if not self.references_version():
            raise ValueError("Missing ref (version info)")

    def is_valid(self) -> bool:
        raise NotImplementedError(OVERRIDE_MSG)

    def validate(self) -> None:
        if not self.is_valid():
            raise ValueError("Invalid HostingUnitId")

    def create_project_hosting_url(self) -> str:
        raise NotImplementedError(OVERRIDE_MSG)

    def create_download_url(self, path: str = None) -> str:
        raise NotImplementedError(OVERRIDE_MSG)


@dataclass(slots=True, frozen=True)
class HostingUnitIdForge(HostingUnitId):
    _hosting_id: HostingId = None
    """The owning user or organization of the project"""
    owner: str = None
    """The path leading up to the repo, if any.
    This is [supported by GitLab](https://docs.gitlab.com/ee/user/group/#group-hierarchy),
    but for example GitHub and ForgeJo (CodeBerg) do not support this."""
    group_hierarchy: str = None
    """The name of the repo/project"""
    repo: str = None
    # """The path within the repo"""
    # path: str = None
    """Could be a branch, tag or commit"""
    ref: str = None

    def to_path_str(self) -> str:
        return f"{self.hosting_id()}/{self.owner}{" / " + self.group_hierarchy if self.group_hierarchy else ''}/{self.repo}{" / " + self.ref if self.ref else ''}"

    def hosting_id(self) -> HostingId:
        return self._hosting_id

    def derive(self, hosting_id=None, owner=None, group_hierarchy=None, repo=None, ref=None) -> HostingId:
        return self.__class__(
            _hosting_id=hosting_id if hosting_id else self.hosting_id(),
            owner=owner if owner else self.owner,
            group_hierarchy=group_hierarchy if group_hierarchy else self.group_hierarchy,
            repo=repo if repo else self.repo,
            ref=ref if ref else self.ref,
        )

    def __eq__(self, other) -> bool:
        return (self.hosting_id() == other.hosting_id() and self.owner == other.owner and
                self.group_hierarchy == other.group_hierarchy and self.repo == other.repo
                # and self.path == other.path
                and self.ref == other.ref)

    def references_version(self) -> bool:
        return self.ref is not None

    def is_valid(self) -> bool:
        return self.hosting_id() and self.owner and self.repo

    @staticmethod
    def path_opt(path_part) -> str:
        return f"/{str(path_part)}" if path_part else ""

    @classmethod
    def from_url(cls, url: str) -> HostingUnitIdForge:
        hosting_id = HostingId.from_url(url)
        # if not (isinstance(url, str) and validators.url(url)):
        #     raise ValueError(f"invalid URL '{url}'")
        parsed_url = urlparse(url)
        domain = parsed_url.hostname
        path_parts = Path(parsed_url.path).relative_to("/").parts

        group_hierarchy = None
        path = None
        ref = None
        # TODO Replace all the following with regex matching (with named capture groups)
        match hosting_id:
            case HostingId.GITHUB_COM | HostingId.CODEBERG_ORG:  # FIXME Codeberg is not handled right here
                owner = path_parts[0] if len(path_parts) >= 1 else None
                repo = path_parts[1] if len(path_parts) >= 2 else None
                if domain == "raw.githubusercontent.com":
                    ref = path_parts[2] if len(path_parts) >= 3 else None
                    path = "/".join(path_parts[3:]) if len(path_parts) >= 4 else None
                else:
                    if len(path_parts) >= 4 and path_parts[2] in ["tree", "blob", "raw"]:
                        ref = path_parts[3]
                        if len(path_parts) > 4:
                            path = "/".join(path_parts[4:])
                    elif len(path_parts) > 4 and path_parts[2] == "releases" and path_parts[3] == "tag":
                        ref = path_parts[4]
                    elif len(path_parts) > 3 and path_parts[2] == "commit":
                        ref = path_parts[3]
                    # else:
                    #     raise NotImplementedError(f"Unknown or invalid path format: '{parsed_url.path}'; for platform {hosting_id}.")

            case HostingId.GITLAB_COM:
                owner = path_parts[0] if len(path_parts) >= 1 else None
                repo = path_parts[1] if len(path_parts) >= 2 else None
                # FIXME GitLab URL path parsing needs work here. We still need to set repo_path!
                if len(path_parts) >= 5 and path_parts[2] == "-" and path_parts[3] in ["tree", "blob", "raw"]:
                    ref = path_parts[4]
                    if len(path_parts) > 5:
                        path = "/".join(path_parts[5:])
                elif len(path_parts) >= 5 and path_parts[2] == "-" and path_parts[3] in ["commit", "tags"]:
                    ref = path_parts[4]

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
            group_hierarchy=group_hierarchy,
            repo=repo,
            ref=ref,
            # path=path,
        )

        return (hosting_unit_id, path)

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
                url_path = f"/{self.owner}{self.path_opt(self.group_hierarchy)}/{self.repo}"

            case HostingId.APPROPEDIA_ORG | HostingId.OSHWA_ORG | HostingId.THINGIVERSE_COM:
                raise NotImplementedError(f"This is not a forge(-like) hosting Id: {self.hosting_id()}."
                                          " Please use HostingUnitIdWebById instead.")

            case _:
                raise ValueError(f"Unknown hosting ID '{self.hosting_id()}'")

        return create_url(
            domain=url_domain,
            path=url_path,
        )

    def create_download_url(self, path: str = None) -> str:
        self.validate()

        match self.hosting_id():
            case HostingId.CODEBERG_ORG:
                # format: https://codeberg.org/elevont/ontprox/raw/branch/master/.gitignore
                ref_opt = self.ref if self.ref else "HEAD"
                url_domain = "codeberg.org"
                url_path = f"/{self.owner}/{self.repo}/raw/{ref_opt}{self.path_opt(path)}"

            case HostingId.GITHUB_COM:
                # format: https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}
                # self.check_is_versioned()
                ref_opt = self.ref if self.ref else "HEAD"
                url_domain = "raw.githubusercontent.com"
                url_path = f"/{self.owner}/{self.repo}/{ref_opt}{self.path_opt(path)}"

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
                url_path = f"/{self.owner}/{self.group_hierarchy}/{self.repo}/-/raw/{ref_opt}{self.path_opt(path)}"

            case HostingId.APPROPEDIA_ORG | HostingId.OSHWA_ORG | HostingId.THINGIVERSE_COM:
                raise NotImplementedError(f"This is not a forge(-like) hosting Id: {self.hosting_id()}."
                                          " Please use HostingUnitIdWebById instead.")

            case _:
                raise ValueError(f"Unknown hosting ID '{self.hosting_id()}'")

        return create_url(
            domain=url_domain,
            path=url_path,
        )


@dataclass(slots=True, frozen=True)
class HostingUnitIdWebById(HostingUnitId):
    _hosting_id: HostingId = None
    """The name or other ID of the repo/project"""
    project_id: str = None

    def to_path_str(self) -> str:
        return f"{self.hosting_id()}/{self.project_id}"

    def hosting_id(self) -> HostingId:
        return self._hosting_id

    def __eq__(self, other) -> bool:
        return (self.hosting_id() == other.hosting_id() and self.project_id == other.project_id)

    def references_version(self) -> bool:
        return False

    @classmethod
    def from_url(cls, url: str) -> HostingUnitIdWebById:
        hosting_id = HostingId.from_url(url)
        # if not (isinstance(url, str) and validators.url(url)):
        #     raise ValueError(f"invalid URL '{url}'")
        parsed_url = urlparse(url)
        path_parts = Path(parsed_url.path).relative_to("/").parts

        project_id = None
        path = None
        match hosting_id:
            case HostingId.GITHUB_COM | HostingId.CODEBERG_ORG | HostingId.GITLAB_COM:
                raise NotImplementedError(f"This is not a simple, web-hosted projects platform URL: '{url}';"
                                          " Please parse it as a HostingUnitIdForge instead.")

            case HostingId.APPROPEDIA_ORG:
                # example: <https://www.appropedia.org/Open_Source_Digitally_Replicable_Lab-Grade_Scales>
                if len(path_parts) > 1:
                    raise ParserError(f"Project URLs on platform {hosting_id} only have one path part.")
                project_id = path_parts[0]
                path = None

            case HostingId.OSHWA_ORG:
                # example: <https://certification.oshwa.org/br000010.html>
                if len(path_parts) > 1:
                    raise ParserError(f"Project URLs on platform {hosting_id} only have one path part.")
                project_id = path_parts[0].replace(".html", "")
                path = None

            case HostingId.THINGIVERSE_COM:
                # example: <https://www.thingiverse.com/thing:3062487>
                # example: <blob:https://www.thingiverse.com/e5d97e54-3719-42d3-a037-cd8d2cd7d6f8>
                # parsed = re.search('^https?://www.thingiverse.com/thing:([0-9]+)/?$', id.as_download_url(), re.IGNORECASE)
                if len(path_parts) < 1:
                    raise ParserError(f"Project URLs on platform {hosting_id} have at least one path part.")
                id_parts = path_parts[0].split(":")
                if len(id_parts) < 2 or not id_parts[0] == "thing":
                    raise ParserError(f"Not a thing URL: '{url}'.")
                project_id = id_parts[1]
                path = None

            case _:
                raise NotImplementedError(f"Unknown hosting ID '{hosting_id}'")

        return (cls(
            _hosting_id=hosting_id,
            project_id=project_id,
        ), path)

    def is_valid(self) -> bool:
        return self.hosting_id() and self.project_id

    def create_project_hosting_url(self) -> str:
        self.validate()

        match self.hosting_id():
            case HostingId.GITHUB_COM | HostingId.CODEBERG_ORG | HostingId.GITLAB_COM:
                raise NotImplementedError(f"This is not supported by this DataHostingUnit type: {self.hosting_id()}."
                                          " Please try HostingUnitIdForge instead.")

            case HostingId.APPROPEDIA_ORG:
                url_domain = "www.appropedia.org"
                url_path = f"/{self.project_id}"

            case HostingId.OSHWA_ORG:
                url_domain = "certification.oshwa.org"
                url_path = f"/{self.project_id.lower()}.html"

            case HostingId.THINGIVERSE_COM:
                url_domain = "www.thingiverse.com",
                url_path = f"/thing:{self.project_id}"

            case _:
                raise ValueError(f"Unknown hosting ID '{self.hosting_id()}'")

        return create_url(
            domain=url_domain,
            path=url_path,
        )

    def create_download_url(self, path: str = None) -> str:
        self.validate()

        match self.hosting_id():
            case HostingId.GITHUB_COM | HostingId.CODEBERG_ORG | HostingId.GITLAB_COM:
                raise NotImplementedError(f"This is not supported by this DataHostingUnit type: {self.hosting_id()}."
                                          " Please try HostingUnitIdForge instead.")

            case HostingId.APPROPEDIA_ORG | HostingId.OSHWA_ORG:
                raise NotImplementedError(
                    f"This platform does not support downloading individual files: {self.hosting_id()}.")

            case HostingId.THINGIVERSE_COM:
                # NOTE This _might_ work, if the `path` is indeed a download location
                return f"{self.create_project_hosting_url()}/{path}"

            case _:
                raise ValueError(f"Unknown hosting ID '{self.hosting_id()}'")


class HostingUnitIdFactory:

    @classmethod
    def from_url_no_path(cls, url: str) -> HostingUnitId:
        try:
            return HostingUnitIdForge.from_url_no_path(url)
        except ParserError:
            return HostingUnitIdWebById.from_url_no_path(url)

    @classmethod
    def from_url(cls, url: str) -> (HostingUnitId, Path):
        try:
            return HostingUnitIdForge.from_url(url)
        except ParserError:
            return HostingUnitIdWebById.from_url(url)
