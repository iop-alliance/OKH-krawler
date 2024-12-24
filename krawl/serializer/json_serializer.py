from __future__ import annotations

from pathlib import Path

from krawl.model.project import Project
from krawl.serializer import ProjectSerializer
from krawl.serializer.util import json_serialize


def manual_type_mapper(value) -> dict:
    if isinstance(value, Path):
        return str(value)
    raise TypeError


class JsonProjectSerializer(ProjectSerializer):

    @classmethod
    def extensions(cls) -> list[str]:
        return ["json"]

    def serialize(self, project: Project) -> str:
        return json_serialize(project)
