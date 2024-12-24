from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from time import sleep

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from krawl.config import Config
from krawl.errors import FetcherError, ParserError
from krawl.fetcher import Fetcher
from krawl.log import get_child_logger
from krawl.model.hosting_id import HostingId
from krawl.model.hosting_unit import HostingUnitIdWebById
from krawl.model.project import Project
from krawl.model.project_id import ProjectId
from krawl.normalizer.thingiverse import ThingiverseNormalizer
from krawl.repository import FetcherStateRepository

log = get_child_logger("thingiverse")


class ThingiverseFetcher(Fetcher):
    """Fetcher for projects on GitHub.com.

    REST API documentation:

    - General: <https://www.thingiverse.com/developers>
    - Requests: <https://www.thingiverse.com/developers/swagger>
    """
    HOSTING_ID: HostingId = HostingId.THINGIVERSE_COM
    RETRY_CODES = [429, 500, 502, 503, 504]
    CONFIG_SCHEMA = Fetcher._generate_config_schema(long_name="thingiverse", default_timeout=10, access_token=True)

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

    def __fetch_one(self, hosting_unit_id: HostingUnitIdWebById, last_visited: datetime) -> Project:
        thing_id = hosting_unit_id.project_id
        log.info("Try to fetch thing with id %d", thing_id)
        # Documentation for this call:
        # <https://www.thingiverse.com/developers/swagger#/Thing/get_things__thing_id_>
        thing = self._do_request(f"https://api.thingiverse.com/things/{thing_id}")

        log.info("Convert thing %s...", thing.get('name'))

        # Documentation for this call:
        # <https://www.thingiverse.com/developers/swagger#/Thing/get_things__thing_id__files>
        thing_files = self._do_request(f"https://api.thingiverse.com/things/{thing_id}/files")

        thing['lastVisited'] = last_visited
        thing["fetcher"] = self.HOSTING_ID
        thing["files"] = thing_files

        project = self._normalizer.normalize(thing)
        if not project:
            raise FetcherError(f"project with name {thing['name']} could not be normalized")

        log.info("%d requests triggered", self._request_counter)

        # save current progress
        self._state_repository.store(self.HOSTING_ID, {"id_cursor": id_cursor, "fetch_things_ids": fetch_things_ids})

        return project

    def fetch(self, id: ProjectId) -> Project:
        try:
            hosting_unit_id = HostingUnitIdWebById.from_url_no_path(id.uri)
        except ParserError as err:
            raise FetcherError(f"Invalid Thingiverse thing URL: '{id.uri}'") from err
        last_visited = datetime.now(timezone.utc)
        return self.__fetch_one(hosting_unit_id, last_visited)

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

    def fetch_all(self, start_over=False) -> Generator[Project]:
        id_cursor = 0
        projects_counter = 0
        fetch_things_ids = []

        if start_over:
            self._state_repository.delete(self.HOSTING_ID)
        else:
            state = self._state_repository.load(self.HOSTING_ID)
            if state:
                id_cursor = state.get("id_cursor", 1)
                fetch_things_ids = state.get("fetch_things_ids", [])

        # Documentation for this call:
        # <https://www.thingiverse.com/developers/swagger#/Thing/get_things__thing_id__files>
        data = self._do_request(
            "https://api.thingiverse.com/search",
            {
                'sort': 'newest',
                "type": "things",
                # "license": "cc",
                # "license": "cc-sa",
                # "license": "cc-nd", # Bad
                # "license": "cc-nc", # Bad
                # "license": "cc-nc-sa", # Bad
                # "license": "cc-nc-nd", # Bad
                # "license": "pd0",
                # "license": "gpl",
                # "license": "lgpl",
                # "license": "bsd",
                # "license": "none", # Bad
                "license": "nokia",  # Bad
                # "license": "public",
                "per_page": 30
            })

        log.info("Found things (total): %d", data["total"])
        log.info("Found things (len(hits)): %d", len(data["hits"]))
        log.info("-----------------------")
        log.info("All received data: %d", data)
        log.info("-----------------------")
        first_thing_id = data["hits"][0]["id"]
        last_thing_id = data["hits"][-1]["id"]
        log.info("First thing ID: %d", first_thing_id)
        log.info("Last thing ID: %d", last_thing_id)
        log.info("Found things: %d", last_thing_id - first_thing_id)
        return None

        last_thing_id = data["hits"].pop(0)["id"]
        last_visited = datetime.now(timezone.utc)

        while id_cursor < last_thing_id:  # TODO Should this not rather be `<=`?
            fetch_things_ids.append(id_cursor)
            id_cursor += 1
            try:
                thing_id = TODO
                hosting_unit_id = HostingUnitIdWebById(_hosting_id=self.HOSTING_ID, project_id=thing_id)
                project = self.__fetch_one(hosting_unit_id, last_visited)
                log.debug("yield project #%d: %s", projects_counter, project.id)
                projects_counter += 1
                yield project
            except FetcherError as err:
                log.warning(err)
                continue
