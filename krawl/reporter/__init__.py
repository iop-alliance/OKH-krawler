from __future__ import annotations

from enum import Enum

from krawl.project import Project, ProjectID


class Status(str, Enum):
    UNKNOWN = "unknown"
    OK = "ok"
    FAILED = "failed"

    def __str__(self) -> str:
        return self.name


class Reporter:
    """Interface for creating a fetching report."""

    def add(self, project_id: ProjectID, status: Status, reasons: list[str] = None, project: Project = None) -> None:
        """Add an entry to the report."""
        raise NotImplementedError()

    def close(self) -> None:
        """Closes the underlying resources."""
        raise NotImplementedError()

    def __del__(self):
        self.close()
