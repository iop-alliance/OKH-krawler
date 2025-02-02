from __future__ import annotations

from krawl.normalizer import Normalizer
from krawl.project import Project


class ProjectSerializer:
    """Interface for serializing project metadata."""

    def serialize(self, project: Project) -> str:
        raise NotImplementedError()


class ProjectDeserializer:
    """Interface for deserializing project metadata."""

    def deserialize(self, serialized: str | bytes, normalizer: Normalizer, enrich: dict = None) -> Project:
        raise NotImplementedError()
