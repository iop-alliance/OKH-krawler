# SPDX-FileCopyrightText: 2021 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from collections.abc import Generator
from enum import StrEnum

from krawl.fetcher.result import FetchResult
from krawl.model.hosting_id import HostingId
from krawl.model.project import Project
from krawl.model.project_id import ProjectId


class ProjectRepositoryType(StrEnum):
    FILE = "file"
    TRIPLE_STORE = "triple_store"


class ProjectRepository:
    """Interface for storing crawled projects metadata."""

    TYPE: ProjectRepositoryType
    CONFIG_SCHEMA: dict

    def load(self, id: ProjectId) -> Project:
        raise NotImplementedError()

    def load_all(self, id: ProjectId) -> Generator[Project]:
        raise NotImplementedError()

    # def store(self, project: Project) -> None:
    def store(self, fetch_result: FetchResult, project: Project) -> None:
        raise NotImplementedError()

    def contains(self, id: ProjectId) -> bool:
        raise NotImplementedError()

    def search(self,
               platform: str | None = None,
               owner: str | None = None,
               name: str | None = None) -> Generator[Project]:
        raise NotImplementedError()

    def delete(self, id: ProjectId) -> None:
        raise NotImplementedError()


class FetcherStateRepository:

    def load(self, fetcher: HostingId) -> dict:
        raise NotImplementedError()

    def store(self, fetcher: HostingId, state: dict) -> None:
        raise NotImplementedError()

    def delete(self, fetcher: HostingId) -> bool:
        raise NotImplementedError()
