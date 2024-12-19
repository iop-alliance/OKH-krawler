from __future__ import annotations

from pathlib import Path

from krawl.project import Project, ProjectID
from krawl.reporter import Reporter, Status


class FileReporter(Reporter):
    """Reporter on fetching results, that writes to a given file."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._file = None
        self._open(path)

    def add(self, project_id: ProjectID, status: Status, reasons: list[str] = None, project: Project = None) -> None:
        """Add an entry to the report."""
        match status:
            case Status.OK | Status.UNKNOWN:
                line = f"{str(status):<8}: {str(project_id)}\n"
            case Status.FAILED:
                line = f"{str(status):<8}: {str(project_id)} : {', '.join(reasons)}\n"
            case _:
                raise ValueError(f"unknown status: {status}")
        self._file.write(line)

    def close(self) -> None:
        """Closes the underlying resources."""
        if self._file:
            self._file.close()

    def _open(self, path: Path):
        if path.exists() and not path.is_file():
            raise OSError(f"'{path}' is not a file")
        self._file = path.open("w")
