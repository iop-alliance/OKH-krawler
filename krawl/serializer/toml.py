from __future__ import annotations

import toml

from krawl.project import Project
from krawl.serializer import ProjectSerializer


class TOMLProjectSerializer(ProjectSerializer):

    def serialize(self, project: Project) -> str:
        return toml.dumps(project.as_dict())

    def deserialize(self, serialized: str) -> Project:
        deserialized = toml.loads(serialized)
        return Project.from_dict(deserialized)
