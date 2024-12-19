from __future__ import annotations

from collections.abc import Generator

from krawl.project import Project, ProjectID


class Fetcher:
    """Interface for fetching projects."""

    # Domain name of the platform
    NAME = None
    # configuration validation schema, see Cerberus for more information:
    # https://docs.python-cerberus.org/en/stable/validation-rules.html
    CONFIG_SCHEMA = None

    def fetch(self, id: ProjectID) -> Project:
        """Fetch metadata of a single project.

        Args:
            id (ProjectID): The project to be fetched.
        """
        raise NotImplementedError()

    def fetch_all(self, start_over=True) -> Generator[Project]:
        """Find and fetch metadata of all projects on the platform.

        Args:
            start_over (bool, optional): Start the search and fetching process
                over again instead of starting at the last fetched batch.
                Defaults to True.

        Yields:
            Generator[Project, None, None]: The next project found and fetched.
        """
        raise NotImplementedError()
