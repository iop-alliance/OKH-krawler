from __future__ import annotations

from krawl.project import Project


class ProjectSerializer:
    """Interface for serializing and desearlizing project metadata."""

    def serialize(self, project: Project) -> str:
        raise NotImplementedError()

    def deserialize(self, serialized: str) -> Project:
        raise NotImplementedError()
