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
