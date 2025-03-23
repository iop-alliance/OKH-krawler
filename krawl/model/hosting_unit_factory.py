# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from pathlib import Path

from krawl.errors import ParserError
from krawl.model.hosting_unit import HostingUnitId
from krawl.model.hosting_unit_forge import HostingUnitIdForge
from krawl.model.hosting_unit_web import HostingUnitIdWebById


class HostingUnitIdFactory:

    @classmethod
    def from_url_no_path(cls, url: str) -> HostingUnitId:
        try:
            return HostingUnitIdForge.from_url_no_path(url)
        except ParserError:
            return HostingUnitIdWebById.from_url_no_path(url)

    @classmethod
    def from_url(cls, url: str) -> tuple[HostingUnitId, Path | None]:
        try:
            return HostingUnitIdForge.from_url(url)
        except ParserError:
            return HostingUnitIdWebById.from_url(url)
