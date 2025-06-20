# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from collections.abc import Generator

from krawl.config import Config
from krawl.errors import RepositoryError
from krawl.model.project import Project
from krawl.repository import ProjectRepository, ProjectRepositoryType
from krawl.repository.project_file import ProjectRepositoryFile

_repositories_schemas: dict[ProjectRepositoryType, dict] = {
    ProjectRepositoryFile.TYPE: ProjectRepositoryFile.CONFIG_SCHEMA,
}


class ProjectRepositoryFactory:

    def __init__(self, repositories_config: Config, enabled: list[str] | None = None) -> None:
        self._repositories: dict = {}
        self._enabled = enabled or list(_repositories_schemas.keys())

        for e in self._enabled:
            assert e in _repositories_schemas

        self._init_repositories(repositories_config, self._enabled)

    @property
    def enabled(self) -> list[str]:
        return self._enabled

    @classmethod
    def get_config_schemas(cls,
                           proj_repo_types: list[ProjectRepositoryType] | None = None
                          ) -> dict[ProjectRepositoryType, dict]:
        if not proj_repo_types:
            return _repositories_schemas
        schema = {}
        for proj_repo_type in proj_repo_types:
            if proj_repo_type not in _repositories_schemas:
                raise RepositoryError(
                    f"no such repository '{proj_repo_type}', available are: {', '.join(_repositories_schemas.keys())}")
            schema[proj_repo_type] = _repositories_schemas[proj_repo_type]
        return schema

    @classmethod
    def list_available_repositories(cls) -> list[str]:
        return list(_repositories_schemas)

    @classmethod
    def is_repository_available(cls, name: str) -> bool:
        return name in _repositories_schemas

    def get(self, name: str) -> ProjectRepository:
        if name not in _repositories_schemas:
            raise RepositoryError(
                f"no such repository '{name}', available are: {', '.join(_repositories_schemas.keys())}")
        if name not in self._repositories:
            raise RepositoryError(f"repository '{name}' is not enabled")
        return self._repositories[name]

    def get_all(self) -> Generator[ProjectRepository]:
        yield from self._repositories.values()

    def store(self, project: Project) -> None:
        # TODO: should be parallelized
        for repository in self._repositories.values():
            repository.store(project)

    def _init_repositories(self, repositories_config: Config, enabled: list[str]):
        if "file" in enabled:
            self._repositories["file"] = ProjectRepositoryFile(repositories_config.file)
