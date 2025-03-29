# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass, field

from krawl.model.agent import Agent, AgentRef, Organization
from krawl.model.file import File
from krawl.model.licenses import LicenseCont


@dataclass(slots=True)
class Software:
    """Software data model."""

    release: str
    installation_guide: File | None = None
    documentation_language: list[str] | None = field(default_factory=list)
    license: LicenseCont | None = None
    licensor: list[Agent | AgentRef] | None = field(default_factory=list)
    organization: list[Organization | AgentRef] | None = field(default_factory=list)
