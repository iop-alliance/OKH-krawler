from __future__ import annotations

import json

from krawl.errors import SerializerError
from krawl.project import Project
from krawl.serializer import ProjectSerializer


class JSONProjectSerializer(ProjectSerializer):

    def __init__(self, indent=2, sort_keys=True):
        self._indent = indent
        self._sort_keys = sort_keys

    def serialize(self, project: Project) -> str:
        try:
            serialized = json.dumps(project.as_dict(), indent=self._indent, sort_keys=self._sort_keys)
        except Exception as err:
            raise SerializerError(f"failed to serialize JSON: {err}") from err
        return serialized
