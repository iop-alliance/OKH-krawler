from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass

from krawl.errors import NotOverriddenError
from krawl.model.data_set import DataSet
from krawl.model.hosting_id import HostingId
from krawl.model.manifest import Manifest
from krawl.model.project import Project
from krawl.model.project_id import ProjectId
from krawl.repository import FetcherStateRepository


@dataclass(slots=True, frozen=True)
class FetchResult:
    """The result of a successful fetch of an OSH projects meta-data.
    This might be OKH data, or projects hosting systems native format
    (e.g. whatever the Thingiverse API returns about a project
    (and probably in JSON format)."""
    data_set: DataSet = None  # Meta-data about the crawl
    data: Manifest = None  # The actually main content of the crawl; yummy, yummy data!


@dataclass(slots=True, frozen=True)
class FailedFetch:
    """The result of a failed fetch of an OSH projects meta-data."""
    error: Exception = None


class FetchListener:
    """Receives events of failed or successful fetches of OSH projects"""

    def fetched(self, fetch_result: FetchResult) -> None:
        pass

    def failed_fetch(self, failed_fetch: FailedFetch) -> None:
        pass


class Fetcher:
    """Interface for fetching projects
    from a specific hosting technology
    (e.g. GitHub or IPFS)."""

    # The platform the fetcher can fetch projects from
    HOSTING_ID: HostingId = None
    # configuration validation schema, see Cerberus for more information:
    # https://docs.python-cerberus.org/en/stable/validation-rules.html
    CONFIG_SCHEMA = None

    def __init__(self, state_repository: FetcherStateRepository) -> None:
        self._state_repository: FetcherStateRepository = state_repository
        self._fetch_listeners: list[FetchListener] = []

    def add_fetch_listener(self, listener: FetchListener) -> None:
        self._fetch_listeners.append(listener)

    def _fetched(self, evt: FetchResult) -> None:
        for fetch_listener in self._fetch_listeners:
            fetch_listener.fetched(evt)

    def _failed_fetch(self, evt: FailedFetch) -> None:
        for fetch_listener in self._fetch_listeners:
            fetch_listener.fetched(evt)

    @classmethod
    def _generate_config_schema(cls, long_name: str, default_timeout: int, access_token: bool) -> dict:
        schema = {
            "type": "dict",
            "default": {},
            "meta": {
                "long_name": long_name,
            },
            "schema": {
                "timeout": {
                    "type": "integer",
                    "default": default_timeout,
                    "min": 1,
                    "meta": {
                        "long_name": "timeout",
                        "description": "Max seconds to wait for a not responding service"
                    }
                },
                "retries": {
                    "type": "integer",
                    "default": 3,
                    "min": 0,
                    "meta": {
                        "long_name": "retries",
                        "description": "Number of retries of requests in cases of network errors"
                    }
                },
            },
        }
        if access_token:
            schema["schema"]["access_token"] = {
                "type": "string",
                "coerce": "strip_str",
                "required": True,
                "nullable": False,
                "meta": {
                    "long_name": "access-token",
                    "description": "Personal access token for using the API"
                }
            }
        return schema

    def fetch(self, id: ProjectId) -> FetchResult:
        """Fetch metadata of a single project.

        Args:
            id (ProjectId): The project to be fetched.
        """
        raise NotOverriddenError()

    def fetch_all(self, start_over=True) -> Generator[FetchResult]:
        """Find and fetch metadata of all relevant projects on the platform.

        Args:
            start_over (bool, optional): Start the search and fetching process
                over again instead of starting at the last fetched batch.
                Defaults to True.

        Yields:
            Generator[Project, None, None]: The next project found and fetched.
        """
        raise NotOverriddenError()
