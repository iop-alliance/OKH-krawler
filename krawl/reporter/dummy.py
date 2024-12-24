from __future__ import annotations

from krawl.model.project import Project
from krawl.model.project_id import ProjectId
from krawl.reporter import Reporter, Status


class DummyReporter(Reporter):
    """Reporter on fetching results, that does nothing"""

    def add(self, project_id: ProjectId, status: Status, reasons: list[str] = None, project: Project = None) -> None:
        pass

    def close(self) -> None:
        pass
