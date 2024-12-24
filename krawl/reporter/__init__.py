from __future__ import annotations

from enum import StrEnum

from krawl.model.project import Project
from krawl.model.project_id import ProjectId


class Status(StrEnum):
    UNKNOWN = "unknown"
    OK = "ok"
    FAILED = "failed"

    def __str__(self) -> str:
        return self.name


class Reporter:
    """Interface for creating a fetching report."""

    def add(self, project_id: ProjectId, status: Status, reasons: list[str] = None, project: Project = None) -> None:
        """Add an entry to the report."""
        raise NotImplementedError()

    def close(self) -> None:
        """Closes the underlying resources."""
        raise NotImplementedError()

    def __del__(self):
        self.close()
