# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass, field

from krawl.model.agent import Agent, Organization
from krawl.model.file import File
from krawl.model.licenses import License
from krawl.model.part import Part
from krawl.model.project_id import ProjectId
from krawl.model.software import Software


@dataclass(slots=True)
class Project:  # pylint: disable=too-many-instance-attributes
    """Project data model, based on:
    <http://w3id.org/oseg/ont/okh.ttl>
    """

    name: str
    repo: str
    version: str
    license: License
    licensor: list[Agent] = field(default_factory=list)
    release: str | None = None
    organization: Organization | None = None
    readme: File | None = None
    contribution_guide: File | None = None
    image: list[File] = field(default_factory=list)
    documentation_language: str | None = None
    technology_readiness_level: str | None = None
    documentation_readiness_level: str | None = None
    attestation: list[str] = field(default_factory=list)
    publication: list[str] = field(default_factory=list)
    function: str | None = None
    standard_compliance: list[str] = field(default_factory=list)
    cpc_patent_class: str | None = None
    tsdc: str | None = None
    bom: File | None = None
    manufacturing_instructions: File | None = None
    user_manual: File | None = None
    part: list[Part] = field(default_factory=list)
    software: list[Software] = field(default_factory=list)
    source: list[File] = field(default_factory=list)
    export: list[File] = field(default_factory=list)

    @property
    def id(self) -> ProjectId:
        """Generates an ID in form of 'platform/owner/repo/path'"""
        return ProjectId.from_url(self.repo)
