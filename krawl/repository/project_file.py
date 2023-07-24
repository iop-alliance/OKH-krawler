from __future__ import annotations

from pathlib import Path

from pathvalidate import sanitize_filename

from krawl.config import Config
from krawl.log import get_child_logger
from krawl.project import Project, ProjectID
from krawl.repository import ProjectRepository
from krawl.serializer.rdf_serializer import RDFProjectSerializer
from krawl.serializer.toml_serializer import TOMLProjectSerializer
from krawl.serializer.yaml_serializer import YAMLProjectSerializer

log = get_child_logger("repo_file")


class ProjectRepositoryFile(ProjectRepository):
    """Storing and loading projects metadata."""

    NAME = "file"
    CONFIG_SCHEMA = {
        "type": "dict",
        "default": {},
        "meta": {
            "long_name": "file",
        },
        "schema": {
            "workdir": {
                "type": "path",
                "required": True,
                "nullable": False,
                "default": Path("./workdir"),
                "meta": {
                    "long_name": "workdir",
                    "description": "Base path to store and load projects in the filesystem"
                }
            },
            "format": {
                "type": "set",
                "default": {"toml", "rdf"},
                "allowed": {"toml", "rdf"},
                "meta": {
                    "description": "File formats for storing projects (available: yaml, toml, rdf)"
                },
            },
        },
    }
    FORMATS = {
        "toml": (TOMLProjectSerializer(), "toml"),
        "rdf": (RDFProjectSerializer(), "ttl"),
    }

    def __init__(self, repository_config: Config):
        self._workdir = repository_config.workdir
        self._formats = repository_config.format

    def path_for_id(self, id: ProjectID, extension: str) -> Path:
        sanitized_id = [sanitize_filename(f) for f in str(id).split("/")]
        return (self._workdir / Path(*sanitized_id)) / ("project." + extension)

    # def load(self, id: ProjectID) -> Project:
    #     file_path = self.path_for_id(id)
    #     log.debug("Loading '%s' from '%s'", id, str(file_path))
    #     serialized = file_path.read_text()
    #     project = self._serializer.deserialize(serialized)
    #     return project

    # def load_all(self, id) -> Generator[Project, None, None]:
    #     paths = self._workdir.glob("**/*." + self._extension)
    #     for p in paths:
    #         id = str(p.relative_to(self._workdir).with_suffix(""))
    #         yield self.load(id)

    def store(self, project: Project) -> None:
        for format in self._formats:
            serializer, extension = self.FORMATS[format]
            file_path = self.path_for_id(project.id, extension)
            log.debug("saving '%s' to '%s'", project.id, str(file_path))
            file_path.parent.mkdir(parents=True, exist_ok=True)
            serialized = serializer.serialize(project)
            file_path.write_text(serialized)

    # def contains(self, id: str) -> bool:
    #     file_path = self.path_for_id(id)
    #     return file_path.exists() and file_path.is_file()

    # def search(self,
    #            platform: str | None = None,
    #            owner: str | None = None,
    #            name: str | None = None) -> Generator[Project, None, None]:
    #     raise NotImplementedError()

    # def delete(self, id: str) -> None:
    #     file_path = self.path_for_id(id)
    #     log.debug("deleting '%s' (%s)", id, str(file_path))
    #     if not file_path.exists():
    #         raise RepositoryException("no such project")
    #     # remove file
    #     file_path.unlink()
    #     # remove parent dirs if empty
    #     project_dir = file_path.parent
    #     if list(project_dir.iterdir()):
    #         return
    #     project_dir.rmdir()
    #     owner_dir = file_path.parent
    #     if list(owner_dir.iterdir()):
    #         return
    #     owner_dir.rmdir()
    #     platform_dir = file_path.parent
    #     if list(platform_dir.iterdir()):
    #         return
    #     platform_dir.rmdir()
