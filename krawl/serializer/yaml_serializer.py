from __future__ import annotations

import yaml

from krawl.project import Project
from krawl.serializer import ProjectSerializer


class YAMLProjectSerializer(ProjectSerializer):

    def __init__(self, indent=2, sort_keys=True):
        self._indent = indent
        self._sort_keys = sort_keys

    def serialize(self, project: Project) -> str:
        return yaml.safe_dump(project.as_dict(), indent=self._indent, sort_keys=self._sort_keys)
