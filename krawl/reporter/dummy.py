from __future__ import annotations

from krawl.model.hosting_unit import HostingUnitId
from krawl.model.project import Project
from krawl.reporter import Reporter, Status


class DummyReporter(Reporter):
    """Reporter on fetching results, that does nothing"""

    def add(self,
            hosting_unit_id: HostingUnitId,
            status: Status,
            reasons: list[str] | None = None,
            project: Project | None = None) -> None:
        pass

    def close(self) -> None:
        pass
