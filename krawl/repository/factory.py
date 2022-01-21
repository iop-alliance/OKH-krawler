from __future__ import annotations

from collections.abc import Generator

from krawl.config import Config
from krawl.errors import RepositoryError
from krawl.project import Project
from krawl.repository import ProjectRepository
from krawl.repository.project_file import ProjectRepositoryFile
from krawl.repository.project_wikibase import ProjectRepositoryWikibase

_repositories_schemas = {
    ProjectRepositoryFile.NAME: ProjectRepositoryFile.CONFIG_SCHEMA,
    ProjectRepositoryWikibase.NAME: ProjectRepositoryWikibase.CONFIG_SCHEMA,
}


class ProjectRepositoryFactory:

    def __init__(self, repositories_config: Config, enabled: list[str] = None) -> None:
        self._repositories = {}
        self._enabled = enabled or list(_repositories_schemas.keys())

        for e in enabled:
            assert e in _repositories_schemas

        self._init_repositories(repositories_config, enabled)

    @property
    def enabled(self) -> list[str]:
        return self._enabled

    @classmethod
    def get_config_schemas(cls, names: list[str] = None) -> dict:
        if not names:
            return _repositories_schemas
        schema = {}
        for name in names:
            if name not in _repositories_schemas:
                raise RepositoryError(
                    f"no such repository '{name}', available are: {', '.join(_repositories_schemas.keys())}")
            schema[name] = _repositories_schemas[name]
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
        return self._repositories[id.platform]

    def get_all(self) -> Generator[ProjectRepository, None, None]:
        for repository in self._repositories.values():
            yield repository

    def store(self, project: Project) -> None:
        # TODO: should be parallelized
        for repository in self._repositories.values():
            repository.store(project)

    def _init_repositories(self, repositories_config: Config, enabled: list[str]):
        if "file" in enabled:
            self._repositories["file"] = ProjectRepositoryFile(repositories_config.file)

        if "wikibase" in enabled:
            self._repositories["wikibase"] = ProjectRepositoryWikibase(repositories_config.wikibase)
