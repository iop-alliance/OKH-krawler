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

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self


@dataclass(slots=True, frozen=True)
class HostingUnitIdWebById(HostingUnitId):
    _hosting_id: HostingId
    """The name or other ID of the repo/project"""
    project_id: str

    def to_path_str(self) -> str:
        return f"{self.hosting_id()}/{self.project_id}"

    def hosting_id(self) -> HostingId:
        return self._hosting_id

    def __eq__(self, other) -> bool:
        return (self.hosting_id() == other.hosting_id() and self.project_id == other.project_id)

    def references_version(self) -> bool:
        return False

    @classmethod
    def from_url(cls, url: str) -> tuple[Self, Path | None]:
        hosting_id = HostingId.from_url(url)
        # if not (isinstance(url, str) and validators.url(url)):
        #     raise ValueError(f"invalid URL '{url}'")
        parsed_url = urlparse(url)
        path_parts = Path(parsed_url.path).relative_to("/").parts

        project_id: str
        path: Path | None
        match hosting_id:
            case HostingId.GITHUB_COM | HostingId.CODEBERG_ORG | HostingId.GITLAB_COM:
                raise NotImplementedError(f"This is not a simple, web-hosted projects platform URL: '{url}';"
                                          " Please parse it as a HostingUnitIdForge instead.")

            case HostingId.APPROPEDIA_ORG:
                # example: <https://www.appropedia.org/Open_Source_Digitally_Replicable_Lab-Grade_Scales>
                project_id = parsed_url.path
                if project_id.startswith("/"):
                    project_id = project_id[1:]
                if project_id.endswith("/"):
                    project_id = project_id[:-1]
                path = None

            case HostingId.OSHWA_ORG:
                # example: <https://certification.oshwa.org/br000010.html>
                if len(path_parts) > 1:
                    raise ParserError(
                        f"Project URLs on platform {hosting_id} only have one path part, but got '{url}'.")
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
        return self.hosting_id() is not None and self.project_id is not None

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
                url_domain = "www.thingiverse.com"
                url_path = f"/thing:{self.project_id}"

            case _:
                raise ValueError(f"Unknown hosting ID '{self.hosting_id()}'")

        return create_url(
            domain=url_domain,
            path=url_path,
        )

    def create_download_url(self, path: Path | str) -> str:
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
