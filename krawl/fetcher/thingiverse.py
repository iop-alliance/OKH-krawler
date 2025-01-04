# SPDX-FileCopyrightText: 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2022 Nicolas Traeder <nicolas@konek.to>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
import math
from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime, timezone
from time import sleep
from typing import TypeAlias

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from typing import TypedDict

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
from krawl.model.licenses import License, LicenseType
from krawl.model.manifest import Manifest, ManifestFormat
from krawl.model.project_id import ProjectId
from krawl.model.sourcing_procedure import SourcingProcedure
from krawl.repository import FetcherStateRepository

__long_name__: str = "thingiverse"
__hosting_id__: HostingId = HostingId.THINGIVERSE_COM
__sourcing_procedure__: SourcingProcedure = SourcingProcedure.API
__dataset_license__: License = License(
    _id="LicenseRef-Thingiverse-API",
    name="API License Agreement for the MakerBot Developer Program",
    reference_url="https://www.thingiverse.com/legal/api",
    type_=LicenseType.PROPRIETARY,
    is_spdx=False,
    is_osi_approved=False,
    is_fsf_libre=False,
    is_blocked=True,
)
__dataset_creator__: Organization = Organization(name="Thingiverse", url="https://www.thingiverse.com")
log = get_child_logger(__long_name__)

t_url: TypeAlias = str
t_string: TypeAlias = str
t_datetime: TypeAlias = str

class ThingiverseThingSearch(TypedDict):
    "This maps precisely to the Thingiverse API response of a thing - thing search."
    total: int
    hits: list[Hit]

class Person(TypedDict):
    "This maps precisely to the Thingiverse API response of a thing - person."
    id: int
    name: t_string
    first_name: t_string
    last_name: t_string
    url: t_url
    public_url: t_url
    thumbnail: t_url
    count_of_followers: int
    count_of_following: int
    count_of_designs: int
    make_count: int
    accepts_tips: bool
    is_following: bool
    location: t_string
    cover: t_url
    is_admin: bool
    is_moderator: bool
    is_featured: bool
    is_verified: bool

class ImageSize(TypedDict):
    "This maps precisely to the Thingiverse API response of a thing - image size."
    type: t_string
    size: t_string
    url: t_url

class Image(TypedDict):
    "This maps precisely to the Thingiverse API response of a thing - image."
    id: int
    url: t_url
    name: t_string
    sizes: list[ImageSize]
    added: t_datetime

class Tag(TypedDict):
    "This maps precisely to the Thingiverse API response of a thing - tag."
    name: t_string
    url: t_url
    count: int
    things_url: t_url
    absolute_url: t_string

class ZipFile(TypedDict):
    "This maps precisely to the Thingiverse API response of a thing - zip file."
    name: t_string
    url: t_url

class ZipData(TypedDict):
    "This maps precisely to the Thingiverse API response of a thing - zip data."
    files: list[ZipFile]

class Hit(TypedDict):
    "This maps precisely to the Thingiverse API response of a thing - hit."
    id: int
    name: t_string
    thumbnail: t_url
    url: t_url
    public_url: t_url
    creator: Person
    added: t_datetime
    modified: t_datetime
    is_published: int
    is_wip: int
    is_featured: bool
    is_nsfw: bool
    is_ai: bool
    like_count: int
    is_liked: bool
    collect_count: int
    is_collected: bool
    comment_count: int
    is_watched: bool
    default_image: Image
    description: t_string
    instructions: t_string | None
    description_html: t_string
    instructions_html: t_string
    details: t_string
    details_parts: list[dict]
    edu_details: t_string | None
    edu_details_parts: list[dict]
    license: t_string
    allows_derivatives: bool
    files_url: t_url
    images_url: t_url
    likes_url: t_url
    ancestors_url: t_url
    derivatives_url: t_url
    tags_url: t_string
    tags: list[Tag]
    categories_url: t_url
    file_count: int
    is_purchased: int
    app_id: int | None
    download_count: int
    view_count: int
    education: dict
    remix_count: int
    make_count: int
    app_count: int
    root_comment_count: int
    moderation: t_string | None
    is_derivative: bool
    ancestors: list
    can_comment: bool
    type_name: t_string
    is_banned: bool
    is_comments_disabled: bool
    needs_moderation: int
    is_decoy: int
    zip_data: ZipData


class ThingFile(TypedDict):
    "This maps precisely to the Thingiverse API response of a file - file."
    id: int
    name: t_string
    size: int
    url: t_url
    public_url: t_url
    download_url: t_url
    threejs_url: t_url
    thumbnail: t_url
    default_image: Image
    date: t_datetime
    formatted_size: t_string
    download_count: int
    direct_url: t_url




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
        fetcher_state = _FetcherState.load(self._state_repository, start_over=start_over)

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
