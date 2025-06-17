# SPDX-FileCopyrightText: 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2022 Nicolas Traeder <nicolas@konek.to>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
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
from krawl.model.hosting_unit_web import HostingUnitIdWebById
from krawl.model.licenses import LicenseCont, LicenseType
from krawl.model.manifest import Manifest, ManifestFormat
from krawl.model.project_id import ProjectId
from krawl.model.sourcing_procedure import SourcingProcedure
from krawl.repository import FetcherStateRepository
from krawl.shared.thingiverse import (RETRY_CODES, Hit, StorageThingMeta, ThingSearch, read_all_os_thing_metas,
                                      read_thing_metas_with_path)

__long_name__: str = "thingiverse"
__hosting_id__: HostingId = HostingId.THINGIVERSE_COM
__sourcing_procedure__: SourcingProcedure = SourcingProcedure.API
__dataset_license__: LicenseCont = LicenseCont(
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
    """Fetcher for projects on Thingiverse.com.

    REST API documentation:

    - General: <https://www.thingiverse.com/developers>
    - Requests: <https://www.thingiverse.com/developers/swagger>
    - Legal: <https://www.thingiverse.com/legal/api>

    ## Crux

    Thingiverse has no interest in us (or anyone else) to have
    an easy way to access their meta-data.
    For single projects, yes.
    For all the projects, no.
    In theory, one can get all the projects meta-data through their API.
    In practice however,
    we find that a lot of the advertised functionality does not work,
    and that there are extra limits that are not documented.
    This is all concentrated in the search API.
    One extra limit, for example,
    is that the maximum amount of search results available is 10'000;
    that includes paging, no matter the page-size.
    In theory, the search API allows to select by project 'license',
    'posted_after' and 'posted_before' dates.
    There one might now think, that choosing these values carefully,
    we could shift a variable-size frame through time,
    choosing the time-frame small enough to never surpass the 10k limit
    in the amount of results, but no, no!
    Because 'posted_after' and 'posted_before' are completely non-functional.

    Whatever one might try to come up with,
    they made it not work already.
    There is one weak-spot though, that they will likely not cover:
    Their projects are identified by ID, and these IDs are ascending, meaning:
    The first project ever published had ID 1, the next one 2, and so on,
    and thus ....

    ## Solution

    We simply get the ID of the latest project published,
    which we *can* do with the help of their search-API,
    and then we painstakingly go through all the (potential) project IDs
    from 1 till that ID, trying to fetch each one.
    Because this takes a LOT of time, due to the 1 project fetch per second rate limit,
    we make sure to cache the results in a way that is not only easily reusable by us,
    but potentially also other projects.
    IDs we tried to fetch once, but turned out to be deleted projects,
    we never have to fetch again.
    Projects we fetched but turned out to not be Open Source,
    we may choose to never fetch again as well,
    or just once a year or so,
    to check if they may have changed the license.

    All the raw fetch-results are stored in a git repo,
    exactly as we get them from the API,
    if the project is Open Source.
    For all the IDs we tried to fetch,
    we store the ID, fetch-date, and state (Open Source|proprietary|deleted).
    And we store the latest ID we tried fetched, separately.
    """
    CONFIG_SCHEMA = Fetcher._generate_config_schema(long_name=__long_name__, default_timeout=10, access_token=True)

    def __init__(self, state_repository: FetcherStateRepository, config: Config) -> None:
        super().__init__(state_repository=state_repository)
        # self._normalizer = self.create_normalizer()

        # self._repo_cache = {}
        # self._rate_limit = {}
        self._request_counter = 0
        self._request_start_time = None
        self.config = config

        retry = Retry(
            total=config.retries,
            backoff_factor=15,
            status_forcelist=RETRY_CODES,
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

    def __fetch_one(self,
    # fetcher_state: _FetcherState,
    hosting_unit_id: HostingUnitIdWebById, last_visited: datetime,
                    meta: StorageThingMeta, raw_thing: Hit) -> FetchResult:
        try:
            thing_id = hosting_unit_id.project_id
            log.info("Try to fetch thing with id %s", thing_id)
            # raw_project: dict[str, Any] = {}
            # Documentation for this call:
            # <https://www.thingiverse.com/developers/swagger#/Thing/get_things__thing_id_>
            # raw_thing: Hit = self._do_request(f"https://api.thingiverse.com/things/{thing_id}")
            # raw_project["thing"] = raw_thing
            raw_project: Hit = raw_thing

            log.info("Convert thing (%s) '%s' ...", thing_id, raw_thing.get('name'))

            # NOTE We do not need this, because while this gives us a LOT of info
            #      about each file in the project,
            #      The essential info - and really all we need -
            #      is already in `Hit.zip`.
            # # Documentation for this call:
            # # <https://www.thingiverse.com/developers/swagger#/Thing/get_things__thing_id__files>
            # raw_files: list[ThingFile] = self._do_request(f"https://api.thingiverse.com/things/{thing_id}/files")
            # raw_project["files"] = raw_files

            last_visited = meta["last_scrape"]
            data_set = DataSet(
                okhv_fetched="OKH-LOSHv1.0",  # FIXME Not good, not right
                crawling_meta=CrawlingMeta(
                    sourcing_procedure=__sourcing_procedure__,
                    last_visited=last_visited,
                    first_visited=last_visited,
                    last_successfully_visited=last_visited,
                    last_detected_change=None,
                    created_at=None,
                    visits=1,
                    changes=0,
                    manifest=None,
                ),
                hosting_unit_id=hosting_unit_id,
                license=__dataset_license__,
                licensor=[__dataset_creator__],
            )

            # fetch_result = FetchResult(data_set=data_set,
            #                            data=Manifest(content=json.dumps(raw_project, indent=2),
            #                                          format=ManifestFormat.JSON))
            fetch_result = FetchResult(data_set=data_set,
                                       data=Manifest(content=dict(raw_project), format=ManifestFormat.JSON))

            # project = self._normalizer.normalize(raw_project)
            # if not project:
            #     raise FetcherError(f"project with name {raw_project['name']} could not be normalized")

            log.info("%d requests triggered", self._request_counter)

            self._fetched(fetch_result)

            # save current progress
            # fetcher_state = _FetcherState.load(self._state_repository)
            # fetcher_state.next_fetch += 1
            # fetcher_state.fetched_ids.append(thing_id)
            # fetcher_state.store(self._state_repository)
            return fetch_result
        except FetcherError as err:
            self._failed_fetch(FailedFetch(hosting_unit_id=hosting_unit_id, error=err))
            raise err

    def fetch(self, project_id: ProjectId) -> FetchResult:
        try:
            hosting_unit_id: HostingUnitIdWebById = HostingUnitIdWebById.from_url_no_path(project_id.uri)

            thing_id: str = hosting_unit_id.project_id
            thing_id_num: int = int(thing_id)
            slice_min_id: int = (thing_id_num // 1000) * 1000
            slice_file_path = Path(f"rust/workdir/thingiverse_store/data/{slice_min_id}/open_source.csv")

            thing_meta: StorageThingMeta | None = None
            thing: Hit | None = None
            for (thing_meta_cur, thing_api_json_file) in read_thing_metas_with_path(slice_file_path):
                thing_id_cur: int = thing_meta_cur['id']
                if thing_id_cur != thing_id_num:
                    continue
                thing = json.loads(thing_api_json_file.read_text())
            if thing_meta is None or thing is None:
                raise FetcherError(f"Could not find thing with id {thing_id} in rust fetch-results")
        except ParserError as err:
            raise FetcherError(f"Invalid {__hosting_id__} project URL: '{project_id.uri}'") from err
        last_visited = datetime.now(timezone.utc)
        # fetcher_state: _FetcherState = _FetcherState.load(self._state_repository)
        # return self.__fetch_one(fetcher_state, hosting_unit_id, last_visited, thing_meta, thing)
        return self.__fetch_one(hosting_unit_id, last_visited, thing_meta, thing)

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

    def fetch_latest_thing_id(self) -> int:
        # Documentation for this call:
        # <https://www.thingiverse.com/developers/swagger#/Search/get_search__term___type_things>
        data: ThingSearch = self._do_request(
            "https://api.thingiverse.com/search/",
            {
                "type": "things",
                "per_page": 1,
                'sort': 'newest',
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
                # "license": "nokia",  # Bad
                # "license": "public",
            })

        hits: list[Hit] = data["hits"]
        if hits == []:
            raise FetcherError("Failed to fetch the latest thing-ID")

        return hits[0]["id"]

    def fetch_all(self, start_over=False) -> Generator[FetchResult]:
        projects_counter: int = 0
        # fetcher_state = _FetcherState.load(self._state_repository, start_over=start_over)

        # latest_thing_id: int = self.fetch_latest_thing_id()
        # min_thing_id = self.config.fetch_range.min
        # max_thing_id = min(self.config.fetch_range.max, latest_thing_id)
        # max_thing_id_src = "configured" if self.config.fetch_range.max < latest_thing_id else "latest available"

        # log.info("latest_thing_id: %d", latest_thing_id)
        # log.info("Actual scraping range:")
        # log.info("  min_thing_id (configured): %d", min_thing_id)
        # log.info("  max_thing_id (%s): %d", max_thing_id_src, max_thing_id)

        # last_thing_id = data["hits"].pop(0)["id"]
        last_visited = datetime.now(timezone.utc)

        for (thing_meta, thing_api_json_file) in read_all_os_thing_metas():
            # thing_meta = StorageThingMeta(
            #     id=264461,
            #     state= StorageThingIdState.OPEN_SOURCE,
            #     first_scrape= last_visited,
            #     last_scrape= last_visited,
            #     last_successful_scrape= last_visited,
            #     last_change= None,
            #     attempted_scrapes= 1,
            #     scraped_changes= 0)
            # for (thing_meta, thing_api_json_file) in [thing_meta, Path("264461.json"))]: # HACK
            # for (thing_meta, thing_api_json_file) in read_thing_metas_with_path(
            #         Path("rust/workdir/thingiverse_store/data/264000/open_source.csv")):  # HACK
            thing_id = thing_meta["id"]
            final_proj_file = Path(f"workdir/thingiverse.com/{thing_id}/rdf.ttl")
            if final_proj_file.exists():
                log.debug("Thing %s already fetched; skipping it!", thing_id)
                continue
            # toml_path = TODO
            # ttl_path = TODO
            # if not ttl_path.exists():
            #     self.__fetch_one()
        # for thing_id in range(min_thing_id, max_thing_id):
        # raw_project: dict[str, Any] = {}
            thing: Hit = json.loads(thing_api_json_file.read_text())
            # raw_project["thing"] = thing
            # thing_id: int = thing["id"]
            thing_id_str: str = str(thing_id)
            # fetched_things_ids.append(thing_id)
            # next_total_hit_index += 1
            try:
                hosting_unit_id = HostingUnitIdWebById(_hosting_id=__hosting_id__, project_id=thing_id_str)
                fetch_result = self.__fetch_one(hosting_unit_id, last_visited, thing_meta, thing)
                log.debug("yield fetch result #%d: %s", projects_counter, hosting_unit_id)
                projects_counter += 1
                yield fetch_result
            except FetcherError as err:
                log.warn(err)
                continue
