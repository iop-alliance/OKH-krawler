from __future__ import annotations

import toml

from krawl.errors import SerializerError
from krawl.project import Project
from krawl.serializer import ProjectSerializer


class TOMLProjectSerializer(ProjectSerializer):

    def serialize(self, project: Project) -> str:
        try:
            serialized = toml.dumps(project.as_dict())
        except Exception as err:
            raise SerializerError("failed to serialize TOML: {err}") from err
        return serialized
