from __future__ import annotations

from krawl.project import Project, ProjectID
from krawl.reporter import Reporter, Status


class DummyReporter(Reporter):
    """Reporter on fetching results, that does nothing"""

    def add(self, project_id: ProjectID, status: Status, reasons: list[str] = None, project: Project = None) -> None:
        pass

    def close(self) -> None:
        pass
