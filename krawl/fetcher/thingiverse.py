from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from time import sleep

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from krawl.config import Config
from krawl.errors import FetcherError
from krawl.fetcher import Fetcher
from krawl.log import get_child_logger
from krawl.normalizer.thingiverse import ThingiverseNormalizer
from krawl.project import Project, ProjectID
from krawl.repository import FetcherStateRepository

log = get_child_logger("thingiverse")


class ThingiverseFetcher(Fetcher):
    NAME = "thingiverse.com"
    RETRY_CODES = [429, 500, 502, 503, 504]
    CONFIG_SCHEMA = {
        "type": "dict",
        "default": {},
        "meta": {
            "long_name": "thingiverse",
        },
        "schema": {
            "timeout": {
                "type": "integer",
                "default": 15,
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
            "access_token": {
                "type": "string",
                "coerce": "strip_str",
                "required": True,
                "nullable": False,
                "meta": {
                    "long_name": "access-token",
                    "description": "Personal access token for using the thingiverse API"
                }
            },
        },
    }

    def __init__(self, state_repository: FetcherStateRepository, config: Config) -> None:
        self._state_repository = state_repository
        self._normalizer = ThingiverseNormalizer()

        self._repo_cache = {}
        self._rate_limit = {}
        self._request_counter = 0
        self._request_start_time = None

        retry = Retry(
            total=config.retries,
            backoff_factor=15,
            status_forcelist=self.RETRY_CODES,
        )

        self._session = requests.Session()
        self._session.mount(
            "https://",
            HTTPAdapter(max_retries=retry),
        )
        self._session.headers.update({
            "User-Agent": config.user_agent,
            "Authorization": f"Bearer {config.access_token}",
        })

    def fetch(self, id: ProjectID) -> Project:
        pass

    def _do_request(self, url, params=None):

        if params is None:
            params = {}

        response = self._session.get(url=url, params=params)

        self._request_start_time = datetime.now(timezone.utc)
        self._request_counter += 1

        if response.status_code > 205:
            raise FetcherError(f"failed to fetch projects from Thingiverse: {response.text}")

        sleep(1)  # one request per second rate limit

        return response.json()

    def fetch_all(self, start_over=False) -> Generator[Project, None, None]:
        id_cursor = 0
        projects_counter = 0
        fetch_things_ids = []

        if start_over:
            self._state_repository.delete(self.NAME)
        else:
            state = self._state_repository.load(self.NAME)
            if state:
                id_cursor = state.get("id_cursor", 1)
                fetch_things_ids = state.get("fetch_things_ids", [])

        data = self._do_request("https://api.thingiverse.com/search", {
            'sort': 'newest',
            "type": "things",
            "per_page": 1
        })

        last_thing_id = data["hits"].pop(0)["id"]
        last_visited = datetime.now(timezone.utc)

        while id_cursor < last_thing_id:

            fetch_things_ids.append(id_cursor)
            id_cursor += 1
            log.info("Try to fetch thing with id %d", id_cursor)
            try:
                thing = self._do_request(f"https://api.thingiverse.com/things/{id_cursor}")

                log.info("Convert thing %s...", thing.get('name'))

                thing_files = self._do_request(f"https://api.thingiverse.com/things/{last_thing_id}/files")

                thing['lastVisited'] = last_visited
                thing["fetcher"] = self.NAME
                thing["files"] = thing_files

                project = self._normalizer.normalize(thing)
                if not project:
                    log.warning("project with name %s could not be normalized", thing['name'])
                    continue

                projects_counter += 1

                log.debug("%d yield project %s", projects_counter, project.id)
                log.info("%d requests triggered", self._request_counter)
                yield project

                # save current progress
                self._state_repository.store(self.NAME, {"id_cursor": id_cursor, "fetch_things_ids": fetch_things_ids})

            except FetcherError as e:
                log.warning(e)
                continue
