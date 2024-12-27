from __future__ import annotations

import json
import math
from collections.abc import Generator
from dataclasses import dataclass
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
from krawl.model.agent import Organization
from krawl.model.data_set import CrawlingMeta, DataSet
from krawl.model.hosting_id import HostingId
from krawl.model.hosting_unit import HostingUnitIdWebById
from krawl.model.licenses import License
from krawl.model.licenses import get_by_id_or_name_required as get_license_required
from krawl.model.manifest import Manifest, ManifestFormat
from krawl.model.project_id import ProjectId
from krawl.model.sourcing_procedure import SourcingProcedure
from krawl.normalizer import Normalizer
from krawl.normalizer.thingiverse import ThingiverseNormalizer
from krawl.repository import FetcherStateRepository

__long_name__: str = "thingiverse"
__hosting_id__: HostingId = HostingId.THINGIVERSE_COM
__sourcing_procedure__: SourcingProcedure = SourcingProcedure.API
__dataset_license__: License = None  # TODO  # get_license_required("CC-BY-SA-4.0")
__dataset_creator__: Organization = Organization(name="Thingiverse", url="https://www.thingiverse.com")
log = get_child_logger(__long_name__)


@dataclass(slots=True)
class _FetcherState:
    next_fetch: int
    """The next index to be fetched.
    Its scope is the total amount of projects
    available on the hosting platform,
    sorted in alphabetical order."""
    fetched_ids: list[str]
    """A list of all the thing-IDs of projects
    that were already fetched."""
    total_projects: int | None
    """The amount of total projects found on the platform
    during the last call to :py:func:`fetch_all`."""

    @classmethod
    def load(cls, state_repository: FetcherStateRepository, start_over=False) -> _FetcherState:
        next_fetch: int = 0
        fetched_ids: list[str] = []
        total_projects: int | None = None
        if start_over:
            state_repository.delete(__hosting_id__)
        else:
            state = state_repository.load(__hosting_id__)
            if state:
                next_fetch = state.get("next_fetch", next_fetch)
                fetched_ids = state.get("fetched_ids", fetched_ids)
                total_projects = state.get("total_projects", total_projects)
        return cls(next_fetch=next_fetch, fetched_ids=fetched_ids, total_projects=total_projects)

    def store(self, state_repository: FetcherStateRepository) -> None:
        state_repository.store(__hosting_id__, {
            "next_fetch": self.next_fetch,
            "fetched_ids": self.fetched_ids,
            "total_projects": self.total_projects,
        })


class ThingiverseFetcher(Fetcher):
    """Fetcher for projects on GitHub.com.

    REST API documentation:

    - General: <https://www.thingiverse.com/developers>
    - Requests: <https://www.thingiverse.com/developers/swagger>
    - Legal: <https://www.thingiverse.com/legal/api>
    """
    RETRY_CODES = [429, 500, 502, 503, 504]
    BATCH_SIZE = 30
    # BATCH_SIZE = 1
    CONFIG_SCHEMA = Fetcher._generate_config_schema(long_name=__long_name__, default_timeout=10, access_token=True)

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

    def __fetch_one(self, fetcher_state: _FetcherState, hosting_unit_id: HostingUnitIdWebById,
                    last_visited: datetime) -> FetchResult:
        try:
            thing_id = hosting_unit_id.project_id
            log.info("Try to fetch thing with id %s", thing_id)
            # Documentation for this call:
            # <https://www.thingiverse.com/developers/swagger#/Thing/get_things__thing_id_>
            raw_project = self._do_request(f"https://api.thingiverse.com/things/{thing_id}")

            log.info("Convert thing %s...", raw_project.get('name'))

            # Documentation for this call:
            # <https://www.thingiverse.com/developers/swagger#/Thing/get_things__thing_id__files>
            thing_files = self._do_request(f"https://api.thingiverse.com/things/{thing_id}/files")

            raw_project["files"] = thing_files

            data_set = DataSet(
                okhv="OKH-LOSHv1.0",  # FIXME Not good, not right# FIXME Not good, not right
                crawling_meta=CrawlingMeta(
                    sourcing_procedure=__sourcing_procedure__,
                    # created_at: datetime = None
                    last_visited=last_visited,
                    # manifest=path,
                    # last_changed: datetime = None
                    # history = None,
                ),
                hosting_unit_id=hosting_unit_id,
                license=__dataset_license__,
                creator=__dataset_creator__,
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
            fetcher_state = _FetcherState.load(self._state_repository)
            fetcher_state.next_fetch += 1
            fetcher_state.fetched_ids.append(thing_id)
            fetcher_state.store(self._state_repository)
            return fetch_result
        except FetcherError as err:
            self._failed_fetch(FailedFetch(hosting_unit_id=hosting_unit_id, error=err))
            raise err

    def fetch(self, project_id: ProjectId) -> FetchResult:
        try:
            hosting_unit_id: HostingUnitIdWebById = HostingUnitIdWebById.from_url_no_path(project_id.uri)
        except ParserError as err:
            raise FetcherError(f"Invalid {__hosting_id__} project URL: '{project_id.uri}'") from err
        last_visited = datetime.now(timezone.utc)
        fetcher_state: _FetcherState = _FetcherState.load(self._state_repository)
        return self.__fetch_one(fetcher_state, hosting_unit_id, last_visited)

    def _do_request(self, url, params=None):

        if params is None:
            params = {}

        response = self._session.get(url=url, params=params)

        self._request_start_time = datetime.now(timezone.utc)
        self._request_counter += 1

        if response.status_code > 205:
            raise FetcherError(f"failed to fetch projects from {__hosting_id__}: {response.text}")

        sleep(1)  # one request per second rate limit

        return response.json()

    def fetch_all(self, start_over=False) -> Generator[FetchResult]:
        projects_counter: int = 0
        fetcher_state = _FetcherState.load(self._state_repository, start_over)

        page_id = math.floor(fetcher_state.next_fetch / self.BATCH_SIZE) + 1
        page_thing_index = fetcher_state.next_fetch - ((page_id - 1) * self.BATCH_SIZE)
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

        log.info("Found things (total): %s", data["total"])
        log.info("Found things (len(hits)): %d", len(data["hits"]))
        log.debug("-----------------------")
        log.debug("All received data: %s", str(data))
        log.debug("-----------------------")
        # first_thing_id = data["hits"][0]["id"]
        # last_thing_id = data["hits"][-1]["id"]
        # log.info("First thing ID: %d", first_thing_id)
        # log.info("Last thing ID: %d", last_thing_id)
        # log.info("Found things: %d", last_thing_id - first_thing_id)
        # return None

        # last_thing_id = data["hits"].pop(0)["id"]
        last_visited = datetime.now(timezone.utc)

        for hit_idx in range(page_thing_index, len(data["hits"])):
            raw_project = data["hits"][hit_idx]
            thing_id = raw_project["id"]
            # fetched_things_ids.append(thing_id)
            # next_total_hit_index += 1
            try:
                hosting_unit_id = HostingUnitIdWebById(_hosting_id=__hosting_id__, project_id=thing_id)
                fetch_result = self.__fetch_one(fetcher_state, hosting_unit_id, last_visited)
                log.debug("yield fetch result #%d: %s", projects_counter, hosting_unit_id)
                projects_counter += 1
                yield fetch_result
            except FetcherError as err:
                log.warning(err)
                continue
