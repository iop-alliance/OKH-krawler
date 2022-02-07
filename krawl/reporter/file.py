from __future__ import annotations

from pathlib import Path

from krawl.project import Project, ProjectID
from krawl.reporter import Reporter, Status


class FileReporter(Reporter):
    """Reporter on fetching results, that writes to a given file."""

    def __init__(self, path: Path, fetcher_name: str) -> None:
        super().__init__()
        self._file = None
        self._open(path)
        self._fetcher_name = fetcher_name

        self.added_projects = 0
        self.skipped_projects = 0

    def add(self, project_id: ProjectID, status: Status, reasons: list[str] = None, project: Project = None) -> None:
        """Add an entry to the report."""
        if status in (Status.OK, Status.UNKNOWN):
            line = f"{str(status):<8}: {str(project_id)}\n"
            self.added_projects += 1
        elif status == Status.FAILED:
            line = f"{str(status):<8}: {str(project_id)} : {', '.join(reasons)}\n"
            self.skipped_projects += 1

        self._file.write(line)
        self._write_stats()

    def close(self) -> None:
        """Closes the underlying resources."""
        if self._file:
            self._file.close()

    def _open(self, path: Path):
        if path.exists() and not path.is_file():
            raise OSError(f"'{path}' is not a file")
        self._file = path.open("w")

    def _write_stats(self):
        if self._file:
            self._file.writelines([
                "\n\n",
                f"-------- Stats for Fetcher {self._fetcher_name} -------\n\n",
                f"Added projects: {self.added_projects}\n",
                f"Skipped projects: {self.skipped_projects}\n\n"
            ])
