from __future__ import annotations

from pathlib import Path

import orjson

from krawl.errors import SerializerError
from krawl.model.project import Project
from krawl.serializer import ProjectSerializer


def manual_type_mapper(value) -> dict:
    if isinstance(value, Path):
        return str(value)
    raise TypeError


class JsonProjectSerializer(ProjectSerializer):

    @classmethod
    def extensions(cls) -> list[str]:
        return ["json"]

    def serialize(self, project: Project) -> str:
        try:
            serialized = orjson.dumps(project,
                                      default=manual_type_mapper,
                                      option=orjson.OPT_NAIVE_UTC | orjson.OPT_APPEND_NEWLINE | orjson.OPT_INDENT_2 |
                                      orjson.OPT_SORT_KEYS).decode("utf-8")
        except Exception as err:
            raise SerializerError(f"failed to serialize JSON: {err}") from err
        return serialized
