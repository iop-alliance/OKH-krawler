# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from krawl.errors import NotOverriddenError, ParserError
from krawl.model.hosting_id import HostingId

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self
# import validators


@dataclass(slots=True, frozen=True)
class HostingUnitId:
    """A "unit of storage" that holds a single project,
    for example a GitHub repo, a manifest-file or dir in a repo,
    or an IPFS hash.
    """

    @classmethod
    def from_url_no_path(cls, url: str) -> Self:
        hosting_unit_id, path = cls.from_url(url)
        if path:
            raise ParserError(f"Project hosting URL should have no path part: '{url}'")
        return hosting_unit_id

    @classmethod
    def from_url(cls, url: str) -> tuple[Self, Path | None]:
        raise NotOverriddenError()

    def to_path_str(self) -> str:
        raise NotOverriddenError()

    def __str__(self) -> str:
        return self.to_path_str()

    def to_path(self) -> Path:
        return Path(self.to_path_str())

    def hosting_id(self) -> HostingId:
        raise NotOverriddenError()

    def __eq__(self, other) -> bool:
        raise NotOverriddenError()

    def references_version(self) -> bool:
        raise NotOverriddenError()

    def check_is_versioned(self) -> None:
        if not self.references_version():
            raise ValueError("Missing ref (version info)")

    def is_valid(self) -> bool:
        raise NotOverriddenError()

    def validate(self) -> None:
        if not self.is_valid():
            raise ValueError("Invalid HostingUnitId")

    def create_project_hosting_url(self) -> str:
        raise NotOverriddenError()

    def create_download_url(self, path: Path | str) -> str:
        raise NotOverriddenError()
