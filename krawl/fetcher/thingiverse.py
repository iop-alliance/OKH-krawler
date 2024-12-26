from __future__ import annotations

import json
import math
from collections.abc import Generator
from datetime import datetime, timezone
from time import sleep

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from krawl.config import Config
from krawl.errors import FetcherError, ParserError
from krawl.fetcher import Fetcher
from krawl.fetcher.event import FailedFetch
from krawl.fetcher.result import FetchResult
from krawl.log import get_child_logger
from krawl.model.data_set import CrawlingMeta, DataSet
from krawl.model.hosting_id import HostingId
from krawl.model.hosting_unit import HostingUnitIdWebById
from krawl.model.manifest import Manifest, ManifestFormat
from krawl.model.project_id import ProjectId
from krawl.normalizer import Normalizer
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
    BATCH_SIZE = 30
    # BATCH_SIZE = 1
    CONFIG_SCHEMA = Fetcher._generate_config_schema(long_name="thingiverse", default_timeout=10, access_token=True)

    def __init__(self, state_repository: FetcherStateRepository, config: Config) -> None:
        super().__init__(state_repository=state_repository)
        # self._normalizer = self.create_normalizer()

        # self._repo_cache = {}
        # self._rate_limit = {}
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

    @classmethod
    def create_normalizer(cls) -> Normalizer:
        return ThingiverseNormalizer()

    def __fetch_one(self, hosting_unit_id: HostingUnitIdWebById, last_visited: datetime) -> FetchResult:
        try:
            thing_id = hosting_unit_id.project_id
            log.info("Try to fetch thing with id %d", thing_id)
            # Documentation for this call:
            # <https://www.thingiverse.com/developers/swagger#/Thing/get_things__thing_id_>
            raw_project = self._do_request(f"https://api.thingiverse.com/things/{thing_id}")

            log.info("Convert thing %s...", raw_project.get('name'))

            # Documentation for this call:
            # <https://www.thingiverse.com/developers/swagger#/Thing/get_things__thing_id__files>
            thing_files = self._do_request(f"https://api.thingiverse.com/things/{thing_id}/files")

            raw_project["files"] = thing_files

            data_set = DataSet(
                crawling_meta=CrawlingMeta(
                    # created_at: datetime = None
                    last_visited=last_visited,
                    # manifest=path,
                    # last_changed: datetime = None
                    # history = None,
                ),
                hosting_unit_id=hosting_unit_id,
            )

            fetch_result = FetchResult(data_set=data_set,
                                       data=Manifest(content=json.dumps(raw_project, indent=2),
                                                     format=ManifestFormat.JSON))

            # project = self._normalizer.normalize(raw_project)
            # if not project:
            #     raise FetcherError(f"project with name {raw_project['name']} could not be normalized")

            log.info("%d requests triggered", self._request_counter)

            self._fetched(fetch_result)

            # save current progress
            next_total_hit_index, fetched_things_ids = self._get_state()
            next_total_hit_index += 1
            fetched_things_ids.append(thing_id)
            self._set_state(next_total_hit_index, fetched_things_ids)
            return fetch_result
        except FetcherError as err:
            self._failed_fetch(FailedFetch(hosting_unit_id=hosting_unit_id, error=err))
            raise err

    def fetch(self, project_id: ProjectId) -> FetchResult:
        try:
            hosting_unit_id: HostingUnitIdWebById = HostingUnitIdWebById.from_url_no_path(project_id.uri)
        except ParserError as err:
            raise FetcherError(f"Invalid Thingiverse thing URL: '{project_id.uri}'") from err
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

    def _get_state(self, start_over=False) -> tuple[int, list[int]]:
        next_total_hit_index: int = 0
        fetched_things_ids = []
        if start_over:
            self._state_repository.delete(self.HOSTING_ID)
        else:
            state = self._state_repository.load(self.HOSTING_ID)
            if state:
                next_total_hit_index = state.get("next_total_hit_index", 0)
                fetched_things_ids = state.get("fetched_things_ids", [])
        return (next_total_hit_index, fetched_things_ids)

    def _set_state(self, next_total_hit_index: int, fetched_things_ids: list[int]) -> None:
        self._state_repository.store(self.HOSTING_ID, {
            "next_total_hit_index": next_total_hit_index,
            "fetched_things_ids": fetched_things_ids
        })

    def fetch_all(self, start_over=False) -> Generator[FetchResult]:
        projects_counter: int = 0
        next_total_hit_index, _fetched_things_ids = self._get_state(start_over)

        page_id = math.floor(next_total_hit_index / self.BATCH_SIZE) + 1
        page_thing_index = next_total_hit_index - ((page_id - 1) * self.BATCH_SIZE)
        # Documentation for this call:
        # <https://www.thingiverse.com/developers/swagger#/Search/get_search__term___type_things>
        data = self._do_request(
            "https://api.thingiverse.com/search",
            {
                "type": "things",
                "per_page": self.BATCH_SIZE,
                "page": page_id,
                'sort': 'newest',
                # Only show Things posted before this date.
                # Can be a concrete date or "math" like: +1h
                # For more details, see:
                # <https://www.elastic.co/guide/en/elasticsearch/reference/current/common-options.html#date-math>
                # "posted_before": "<some-date-in-the-right-format>",
                # Only show Things posted after this date.
                # Can be a concrete date or "math" like: +1h
                # For more details, see:
                # <https://www.elastic.co/guide/en/elasticsearch/reference/current/common-options.html#date-math>
                # "posted_after": "<some-date-in-the-right-format>",

                # "license": "cc",
                # "license": "cc-sa",
                # "license": "cc-nd", # Bad
                # "license": "cc-nc", # Bad
                # "license": "cc-nc-sa", # Bad
                # "license": "cc-nc-nd", # Bad
                # "license": "pd0",
                # "license": "gpl",
                "license": "lgpl",
                # "license": "bsd",
                # "license": "none", # Bad
                # "license": "nokia",  # Bad
                # "license": "public",
            })

        log.info("Found things (total): %d", data["total"])
        log.info("Found things (len(hits)): %d", len(data["hits"]))
        log.debug("-----------------------")
        log.debug("All received data: %d", data)
        log.debug("-----------------------")
        # first_thing_id = data["hits"][0]["id"]
        # last_thing_id = data["hits"][-1]["id"]
        # log.info("First thing ID: %d", first_thing_id)
        # log.info("Last thing ID: %d", last_thing_id)
        # log.info("Found things: %d", last_thing_id - first_thing_id)
        # return None

        # last_thing_id = data["hits"].pop(0)["id"]
        last_visited = datetime.now(timezone.utc)

        # for raw_project in data["hits"]:
        for hit_idx in range(page_thing_index, len(data["hits"])):
            raw_project = data["hits"][hit_idx]
            thing_id = raw_project["id"]
            # fetched_things_ids.append(thing_id)
            # next_total_hit_index += 1
            try:
                hosting_unit_id = HostingUnitIdWebById(_hosting_id=self.HOSTING_ID, project_id=thing_id)
                fetch_result = self.__fetch_one(hosting_unit_id, last_visited)
                log.debug("yield project #%d: %s", projects_counter, hosting_unit_id)
                projects_counter += 1
                yield fetch_result
            except FetcherError as err:
                log.warning(err)
                continue
