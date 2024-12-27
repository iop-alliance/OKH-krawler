# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass, field

from krawl.model.file import File
from krawl.model.licenses import License
from krawl.model.part import Part
from krawl.model.project_id import ProjectId
from krawl.model.software import Software
from krawl.model.sourcing_procedure import SourcingProcedure


@dataclass(slots=True)
class Project:  # pylint: disable=too-many-instance-attributes
    """Project data model based on
    <https://github.com/iop-alliance/OpenKnowHow/blob/master/res/sample_data/okh-TEMPLATE.toml>. # TODO should be based on okh.ttl instead
    """

    okhv: str = "OKH-LOSHv1.0"
    name: str = None
    repo: str = None
    version: str = None
    release: str = None
    license: License = None
    licensor: str = None
    organization: str = None
    readme: File = None
    contribution_guide: File = None
    image: list[File] = field(default_factory=list)
    documentation_language: str = None
    technology_readiness_level: str = None
    documentation_readiness_level: str = None
    attestation: str = None
    publication: str = None
    function: str = None
    standard_compliance: str = None
    cpc_patent_class: str = None
    tsdc: str = None
    bom: File = None
    manufacturing_instructions: File = None
    user_manual: File = None
    part: list[Part] = field(default_factory=list)
    software: list[Software] = field(default_factory=list)
    sourcing_procedure: SourcingProcedure = None
    source: list[File] = field(default_factory=list)
    export: list[File] = field(default_factory=list)

    @property
    def id(self) -> ProjectId:
        """Generates an ID in form of 'platform/owner/repo/path'"""
        return ProjectId.from_url(self.repo)
