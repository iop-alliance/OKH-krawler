# SPDX-FileCopyrightText: 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2022 Nicolas Traeder <nicolas@konek.to>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

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
# from krawl.model.project import Project
from krawl.normalizer import Normalizer
from krawl.normalizer.oshwa import OshwaNormalizer
from krawl.repository import FetcherStateRepository
from krawl.request.rate_limit import RateLimitFixedTimedelta

# from krawl.util import slugify

__long_name__: str = "oshwa"
__hosting_id__: HostingId = HostingId.OSHWA_ORG
__sourcing_procedure__: SourcingProcedure = SourcingProcedure.API
__dataset_license__: License = get_license_required("CC0-1.0")
__dataset_creator__: Organization = Organization(name="Open Source Hardware Association",
                                                 email="info@oshwa.org",
                                                 url="https://www.oshwa.org")
log = get_child_logger(__long_name__)


class OshwaFetcher(Fetcher):
    RETRY_CODES = [429, 500, 502, 503, 504]
    BATCH_SIZE = 50
    CONFIG_SCHEMA = Fetcher._generate_config_schema(long_name=__long_name__, default_timeout=10, access_token=True)

    def __init__(self, state_repository: FetcherStateRepository, config: Config) -> None:
        super().__init__(state_repository=state_repository)
        # self._normalizer = self.create_normalizer()
        self._rate_limit = RateLimitFixedTimedelta(seconds=5)

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
        return OshwaNormalizer()

    def __fetch_one(self, hosting_unit_id: HostingUnitIdWebById, raw_project: dict,
                    last_visited: datetime) -> FetchResult:
        try:
            # hosting_unit_id = hosting_unit_id.derive(
            #     project_id = slugify(
            #         raw_project["responsibleParty"]),
            #         raw_project["oshwaUid"].lower()
            #     )

            data_set = DataSet(
                okhv="OKH-LOSHv1.0",  # FIXME Not good, not right
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
                                       data=Manifest(content=raw_project, format=ManifestFormat.JSON))
            # try normalizing it
            # try:
            #     raw_project.update(unfiltered_output)
            #     project = self._normalizer.normalize(raw_project)
            # except NormalizerError as err:
            #     raise FetcherError(f"Normalization failed, that should not happen: {err}") from err
            self._fetched(fetch_result)
            return fetch_result
        except FetcherError as err:
            self._failed_fetch(FailedFetch(hosting_unit_id=hosting_unit_id, error=err))
            raise err

    def fetch(self, project_id: ProjectId) -> FetchResult:
        log.debug('Start fetching project %s', project_id)

        hosting_unit_id: HostingUnitIdWebById = HostingUnitIdWebById.from_url_no_path(project_id.uri)

        try:
            hosting_unit_id = HostingUnitIdWebById.from_url_no_path(project_id.uri)
        except ParserError as err:
            raise FetcherError(f"Invalid OSHWA project URL: '{project_id.uri}'") from err

        oshwa_id = hosting_unit_id.project_id

        response = self._session.get(url=f"https://certificationapi.oshwa.org/api/projects/{oshwa_id}",)

        if response.status_code > 205:
            raise FetcherError(f"failed to fetch projects from OSHWA: {response.text}")

        raw_project = response.json()[0]

        last_visited = datetime.now(timezone.utc)

        project = self.__fetch_one(hosting_unit_id, raw_project, last_visited)

        log.debug(f"yield project {hosting_unit_id}")

        return project

    def fetch_all(self, start_over=True) -> Generator[FetchResult]:
        last_offset = 0
        num_fetched = 0
        batch_size = self.BATCH_SIZE
        if start_over:
            self._state_repository.delete(__hosting_id__)
        else:
            state = self._state_repository.load(__hosting_id__)
            if state:
                last_offset = state.get("last_offset", 0)
                num_fetched = state.get("num_fetched", 0)

        while True:
            log.debug("fetching projects %d to %d", num_fetched, num_fetched + batch_size)

            self._rate_limit.apply()
            response = self._session.get(
                url="https://certificationapi.oshwa.org/api/projects",
                params={
                    "limit": batch_size,
                    "offset": last_offset
                },
            )
            self._rate_limit.update()
            if response.status_code > 205:
                raise FetcherError(f"failed to fetch projects from {__hosting_id__}: {response.text}")

            data = response.json()
            last_visited = datetime.now(timezone.utc)
            for raw_project in data["items"]:
                hosting_unit_id = HostingUnitIdWebById(_hosting_id=__hosting_id__, project_id=raw_project['oshwaUid'])
                fetch_result = self.__fetch_one(hosting_unit_id, raw_project, last_visited)
                log.debug("yield fetch_result %s", hosting_unit_id)
                yield fetch_result

            # save current progress
            batch_size = data["limit"]  # in case the batch size will be lowered on the platform in some point in time
            num_fetched += len(data["items"])
            last_offset += batch_size
            if last_offset > data["total"]:
                break

            self._state_repository.store(__hosting_id__, {
                "last_offset": last_offset,
                "num_fetched": num_fetched,
            })

        self._state_repository.delete(__hosting_id__)
        log.debug(f"fetched {num_fetched} projects from {__hosting_id__}")
