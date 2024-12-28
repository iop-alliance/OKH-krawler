# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from collections.abc import Generator

from krawl.errors import NotOverriddenError
from krawl.fetcher.event import FailedFetch, FetchListener
from krawl.fetcher.result import FetchResult
from krawl.model.hosting_id import HostingId
from krawl.model.project_id import ProjectId
from krawl.repository import FetcherStateRepository


class CountingFetchListener(FetchListener):
    """Counts successes and failures"""
    _successes: int = 0
    _failures: int = 0

    def successes(self) -> int:
        return self._successes

    def failures(self) -> int:
        return self._failures

    def fetched(self, _fetch_result: FetchResult) -> None:
        self._successes += 1

    def failed_fetch(self, _failed_fetch: FailedFetch) -> None:
        self._failures += 1


class Fetcher:
    """Interface for fetching projects
    from a specific hosting technology
    (e.g. GitHub or IPFS)."""

    # The platform the fetcher can fetch projects from
    HOSTING_ID: HostingId
    # configuration validation schema, see Cerberus for more information:
    # https://docs.python-cerberus.org/en/stable/validation-rules.html
    CONFIG_SCHEMA: dict

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
            fetch_listener.failed_fetch(evt)

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

    def fetch(self, project_id: ProjectId) -> FetchResult:
        """Fetch metadata of a single project.

        Args:
            project_id (ProjectId): The project to be fetched.
        """
        raise NotOverriddenError()

    def fetch_all(self, start_over=True) -> Generator[FetchResult]:
        """Find and fetch metadata of all relevant projects on the platform.

        Args:
            start_over (bool, optional): Start the search and fetching process
                over again instead of starting at the last fetched batch.
                Defaults to True.

        Yields:
            Generator[FetchResult]: The next project found and fetched.
        """
        raise NotOverriddenError()
