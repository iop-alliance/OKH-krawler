# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass, field

from krawl.model.agent import Agent, AgentRef, Organization
from krawl.model.file import File, Image
from krawl.model.licenses import License
from krawl.model.outer_dimensions import OuterDimensions
from krawl.model.part import Part
from krawl.model.project_id import ProjectId
from krawl.model.software import Software


@dataclass(slots=True)
class Project:  # pylint: disable=too-many-instance-attributes
    """Project data model, based on:
    <http://w3id.org/oseg/ont/okh.ttl>

    What is in the ontology but not here,
    will likely be in `:py:class:krawl.fetcher.result.FetchResult`.
    """

    name: str
    repo: str
    license: License
    licensor: list[Agent | AgentRef] = field(default_factory=list)
    version: str | None = None
    release: str | None = None
    organization: list[Organization | AgentRef] = field(default_factory=list)
    readme: list[File] | None = None
    contribution_guide: File | None = None
    image: list[Image] = field(default_factory=list)
    documentation_language: list[str] = field(default_factory=list)
    technology_readiness_level: str | None = None
    documentation_readiness_level: str | None = None
    attestation: list[str] = field(default_factory=list)
    publication: list[str] = field(default_factory=list)
    function: str | None = None
    standard_compliance: list[str] = field(default_factory=list)
    cpc_patent_class: str | None = None
    tsdc: str | None = None
    bom: list[File] | None = None
    manufacturing_instructions: list[File] = field(default_factory=list)
    user_manual: list[File] | None = None
    mass: float | None = None
    outer_dimensions: OuterDimensions | None = None
    part: list[Part] = field(default_factory=list)
    software: list[Software] = field(default_factory=list)
    source: list[File] = field(default_factory=list)
    export: list[File] = field(default_factory=list)
    auxiliary: list[File] = field(default_factory=list)

    @property
    def id(self) -> ProjectId:
        """Generates an ID in form of 'platform/owner/repo/path'"""
        return ProjectId.from_url(self.repo)
