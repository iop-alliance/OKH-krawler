# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
import urllib.parse
from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from krawl.config import Config
from krawl.errors import FetcherError, NotFound, ParserError
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
from krawl.normalizer.manifest import ManifestNormalizer
from krawl.repository import FetcherStateRepository

__long_name__: str = "appropedia"
__hosting_id__: HostingId = HostingId.APPROPEDIA_ORG
__sourcing_procedure__: SourcingProcedure = SourcingProcedure.GENERATED_MANIFEST
__dataset_license__: License = get_license_required("CC-BY-SA-4.0")
__dataset_creator__: Organization = Organization(name="Appropedia", url="https://www.appropedia.org")
log = get_child_logger(__long_name__)


@dataclass(slots=True)
class _FetcherState:
    next_fetch: int
    """The next index to be fetched.
    Its scope is the total amount of projects
    available on the hosting platform,
    sorted in alphabetical order."""
    fetched_ids: list[str]
    """A list of all the (cleaned up) names of projects
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


class AppropediaFetcher(Fetcher):
    """
    Documentation and tips from Felipe (Admin of Appropedia.org):

    ---

    To get the wiki-text, HTML or semantic data of a set of pages,
    my recommendation is that you first get the list of pages,
    and then query for the wiki-text,
    HTML or semantic data of each.

    To get a list of pages in a category (like `Category:Projects`),
    you can use the following API query:
    <https://www.appropedia.org/w/api.php?action=query&format=json&list=categorymembers&cmlimit=max&cmtitle=Category:Projects>
    See <https://www.appropedia.org/w/api.php?action=help&modules=query>
    for help and more options.

    Another way is to use the search API with the `incategory:Projects` search keyword,
    like so:

    <https://www.appropedia.org/w/api.php?action=query&format=json&list=search&srlimit=max&srsearch=incategory:Projects>

    The nice thing about this is you can easily refine the query
    by adding search terms and keywords,
    like so:

    <https://www.appropedia.org/w/api.php?action=query&format=json&list=search&srlimit=max&srsearch=incategory:Projects+incategory:SDG01_No_poverty>

    (will search for projects that are also in the `Category:SDG01_No_poverty`)
    See <https://www.mediawiki.org/wiki/Help:CirrusSearch>
    for documentation on available search keywords.

    Once you have your list of pages,
    you can easily get the wiki-text,
    HTML or semantic data of each using our REST API, like so:

    - <https://www.appropedia.org/w/rest.php/v1/page/AEF_food_dehydrator>
      (wiki-text and other basic data)
    - <https://www.appropedia.org/w/rest.php/v1/page/AEF_food_dehydrator/html>
      (html)
    - <https://www.appropedia.org/w/rest.php/v1/page/AEF_food_dehydrator/semantic>
      (semantic data)

    ---
    """
    RETRY_CODES = [429, 500, 502, 503, 504]
    CONFIG_SCHEMA = Fetcher._generate_config_schema(long_name=__long_name__, default_timeout=1, access_token=False)

    def __init__(self, state_repository: FetcherStateRepository, config: Config) -> None:
        super().__init__(state_repository=state_repository)

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
        })

    @classmethod
    def create_normalizer(cls) -> Normalizer:
        return ManifestNormalizer()

    @staticmethod
    def url_encode(raw_url_part: str) -> str:
        return urllib.parse.quote_plus(raw_url_part)

    def _download_manifest(self, url) -> bytes:
        # self._file_rate_limit.apply()
        log.debug("downloading manifest file '%s'", url)
        response = self._session.get(url)
        # self._file_rate_limit.update()
        match response.status_code:
            case 200:
                pass
            case _:
                err_desc = '(=> does not exist) ' if response.status_code == 404 else ''
                raise NotFound("Tried to download manifest, but failed with HTTP status code"
                               f" {response.status_code}{err_desc} here: '{url}'")
        return response.content

    def __fetch_one(self, fetcher_state: _FetcherState, hosting_unit_id: HostingUnitIdWebById,
                    last_visited: datetime) -> FetchResult:
        try:
            log.debug('hosting_unit_id.project_id: "%s"', hosting_unit_id.project_id)
            log.debug('hosting_unit_id.project_id (URL-encoded): "%s"', self.url_encode(hosting_unit_id.project_id))
            manifest_dl_url = f"https://www.appropedia.org/scripts/generateOpenKnowHowManifest.php?title={self.url_encode(hosting_unit_id.project_id)}"
            okh_v1_contents = self._download_manifest(manifest_dl_url)
            raw_project = okh_v1_contents

            data_set = DataSet(
                okhv="OKH-v1.0",  # FIXME Not good, not right
                crawling_meta=CrawlingMeta(
                    sourcing_procedure=__sourcing_procedure__,
                    # created_at: datetime = None
                    last_visited=last_visited,
                    manifest=manifest_dl_url,
                    # last_changed: datetime = None
                    # history = None,
                ),
                hosting_unit_id=hosting_unit_id,
                license=__dataset_license__,
                creator=__dataset_creator__,
            )

            fetch_result = FetchResult(data_set=data_set,
                                       data=Manifest(content=raw_project, format=ManifestFormat.YAML))
            fetcher_state.fetched_ids.append(hosting_unit_id.project_id)
            fetcher_state.next_fetch += 1
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
            raise FetcherError(f"Invalid {__hosting_id__} project URL: '{project_id.uri}'") from err

        last_visited = datetime.now(timezone.utc)
        fetcher_state: _FetcherState = _FetcherState.load(self._state_repository)
        fetch_result = self.__fetch_one(fetcher_state, hosting_unit_id, last_visited)
        fetcher_state.store(self._state_repository)
        log.debug(f"yield fetch_result {hosting_unit_id}")

        return fetch_result

    def _download_projects_index(self) -> dict:
        response = self._session.get(
            url=
            "https://www.appropedia.org/w/api.php?action=query&format=json&list=categorymembers&cmlimit=max&cmtitle=Category:Projects",
            headers={
                'Accept': 'application/json',
            },
        )
        if response.status_code > 205:
            raise FetcherError(f"Failed to fetch projects from {__hosting_id__}: {response.text}")
        return response.json()

    def _get_projects_index(self) -> Generator[str]:
        project_list_json = self._download_projects_index()

        # log.debug("Raw fetched project index HTML:\n---\n%s\n---", project_list_html)
        raw_json_file = "appro_raw_proj_index.json"
        with open(raw_json_file, "w") as text_file:
            # text_file.write(json.dump(project_list_json))
            json.dump(project_list_json, text_file)
        # write_to_file(raw_html_file, project_list_html)
        log.debug("Raw fetched project index JSON written to: '%s'", raw_json_file)

        for project in project_list_json["query"]["categorymembers"]:
            yield project["title"]

    def fetch_all(self, start_over=True) -> Generator[FetchResult]:
        project_ids = list(self._get_projects_index())
        project_ids.sort()
        total_projects = len(project_ids)
        log.debug("All fetched Project IDs:\n---\n%s\n---", "\n".join(project_ids))

        proj_idx = -1
        last_visited = datetime.now(timezone.utc)
        fetcher_state: _FetcherState = _FetcherState.load(self._state_repository, start_over=start_over)
        fetcher_state.total_projects = total_projects
        fetcher_state.store(self._state_repository)
        for project_id in project_ids:
            proj_idx += 1
            log.debug("Fetching project %d/%d", proj_idx, total_projects)

            hosting_unit_id = HostingUnitIdWebById(_hosting_id=__hosting_id__, project_id=project_id)
            fetch_result = self.__fetch_one(fetcher_state, hosting_unit_id, last_visited)
            fetcher_state.store(self._state_repository)  # XXX This might be very costly

            yield fetch_result

        self._state_repository.delete(__hosting_id__)
        log.debug(f"fetched {total_projects} projects from {__hosting_id__}")
