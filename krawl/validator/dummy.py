from __future__ import annotations

from krawl.model.project import Project
from krawl.validator import Validator


class DummyValidator(Validator):

    def validate(self, project: Project) -> tuple[bool, list[str]]:
        return True, None
