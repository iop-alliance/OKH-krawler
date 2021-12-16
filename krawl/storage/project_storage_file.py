from __future__ import annotations

import logging
from collections.abc import Generator
from pathlib import Path

from pathvalidate import sanitize_filename

from krawl.exceptions import StorageException
from krawl.project import Project
from krawl.serializer import ProjectSerializer
from krawl.storage import ProjectStorage

log = logging.getLogger("file-project-storage")


class ProjectStorageFile(ProjectStorage):
    """Storing and loading projects metadata."""

    def __init__(self, base_path: Path, extension: str, serializer: ProjectSerializer):
        self._base_path = base_path
        self._extension = extension
        self._serializer = serializer

    def path_for_id(self, id: str) -> Path:
        sanitized_id = [sanitize_filename(f) for f in id.split("/")]
        return (self._base_path / Path(*sanitized_id)) / ("project." + self._extension)

    def load(self, id) -> Project:
        file_path = self.path_for_id(id)
        log.debug("Loading '%s' from '%s'", id, str(file_path))
        serialized = file_path.read_text()
        project = self._serializer.deserialize(serialized)
        return project

    def load_all(self, id) -> Generator[Project, None, None]:
        paths = self._base_path.glob("**/*." + self._extension)
        for p in paths:
            id = str(p.relative_to(self._base_path).with_suffix(""))
            yield self.load(id)

    def store(self, project: Project) -> None:
        file_path = self.path_for_id(project.id)
        log.debug("saving '%s' to '%s'", project.id, str(file_path))
        file_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = self._serializer.serialize(project)
        file_path.write_text(serialized)

    def contains(self, id: str) -> bool:
        file_path = self.path_for_id(id)
        return file_path.exists() and file_path.is_file()

    def search(self,
               platform: str | None = None,
               owner: str | None = None,
               name: str | None = None) -> Generator[Project, None, None]:
        raise NotImplementedError()

    def delete(self, id: str) -> None:
        file_path = self.path_for_id(id)
        log.debug("deleting '%s' (%s)", id, str(file_path))
        if not file_path.exists():
            raise StorageException("no such project")
        # remove file
        file_path.unlink()
        # remove parent dirs if empty
        project_dir = file_path.parent
        if list(project_dir.iterdir()):
            return
        project_dir.rmdir()
        owner_dir = file_path.parent
        if list(owner_dir.iterdir()):
            return
        owner_dir.rmdir()
        platform_dir = file_path.parent
        if list(platform_dir.iterdir()):
            return
        platform_dir.rmdir()
