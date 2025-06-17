# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import re
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
from krawl.model.hosting_unit_web import HostingUnitIdWebById
from krawl.model.licenses import LicenseCont
from krawl.model.licenses import get_by_id_or_name_required as get_license_required
from krawl.model.manifest import Manifest, ManifestFormat
from krawl.model.project_id import ProjectId
from krawl.model.sourcing_procedure import SourcingProcedure
# from krawl.model.project import Project
from krawl.repository import FetcherStateRepository
from krawl.util import url_encode

__long_name__: str = "appropedia"
__hosting_id__: HostingId = HostingId.APPROPEDIA_ORG
__sourcing_procedure__: SourcingProcedure = SourcingProcedure.GENERATED_MANIFEST
__dataset_license__: LicenseCont = get_license_required("CC-BY-SA-4.0")
__dataset_creator__: Organization = Organization(name="Appropedia", url="https://www.appropedia.org")
_re_auto_translated_page_title = re.compile(r".*/[a-z]{2}$")
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
    """\
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
        # print("############")
        # print(url)
        # print("############")
        # print(response.content)
        # print("############")
        # if "Prosthetics" in url:
        #     raise SystemExit(44)
        return response.content

    def __fetch_one(self, fetcher_state: _FetcherState, hosting_unit_id: HostingUnitIdWebById,
                    last_visited: datetime) -> FetchResult:
        log.debug('hosting_unit_id.project_id: "%s"', hosting_unit_id.project_id)
        encoded_project_id: str = url_encode(hosting_unit_id.project_id.replace(" ", "_"))
        log.debug('hosting_unit_id.project_id (URL-encoded): "%s"', encoded_project_id)
        manifest_dl_url = f"https://www.appropedia.org/scripts/generateOpenKnowHowManifest.php?title={encoded_project_id}"
        return self.__fetch_one_raw(fetcher_state, hosting_unit_id, manifest_dl_url, last_visited)

    def __fetch_one_raw(self, fetcher_state: _FetcherState, hosting_unit_id: HostingUnitIdWebById | None,
                        manifest_dl_url: str, last_visited: datetime) -> FetchResult:
        try:
            try:
                okh_v1_contents = self._download_manifest(manifest_dl_url)
            except NotFound as err:
                raise FetcherError(f"Failed to download manifest from '{manifest_dl_url}': {err}") from err
            raw_project = okh_v1_contents

            manifest = Manifest(content=raw_project, format=ManifestFormat.YAML)
            if not hosting_unit_id:
                manifest_data = manifest.as_dict()
                # sample data:
                #     project-link: https://www.appropedia.org/2_FT_Prosthetics
                hosting_unit_id = HostingUnitIdWebById.from_url_no_path(url_encode(manifest_data['project-link']))

            data_set = DataSet(
                okhv_fetched="OKH-v1.0",  # FIXME Not good, not right
                crawling_meta=CrawlingMeta(
                    sourcing_procedure=__sourcing_procedure__,
                    last_visited=last_visited,
                    first_visited=last_visited,
                    last_successfully_visited=last_visited,
                    last_detected_change=None,
                    created_at=None,
                    visits=1,
                    changes=0,
                    manifest=manifest_dl_url,
                ),
                hosting_unit_id=hosting_unit_id,
                license=__dataset_license__,
                licensor=[__dataset_creator__],
                organization=[__dataset_creator__],
            )

            fetch_result = FetchResult(data_set=data_set, data=manifest)
            fetcher_state.fetched_ids.append(hosting_unit_id.project_id)
            fetcher_state.next_fetch += 1
            self._fetched(fetch_result)
            return fetch_result
        except FetcherError as err:
            if not hosting_unit_id:
                hosting_unit_id = HostingUnitIdWebById(
                    _hosting_id=__hosting_id__,
                    project_id=manifest_dl_url,
                )
            self._failed_fetch(FailedFetch(hosting_unit_id=hosting_unit_id, error=err))
            raise err

    def fetch(self, project_id: ProjectId) -> FetchResult:
        log.debug('Start fetching project %s', project_id)

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
            # url="https://www.appropedia.org/w/api.php?action=query&format=json&list=categorymembers&cmlimit=max&cmtitle=Category:Projects",
            url="https://www.appropedia.org/manifests/list.json",

            headers={
                'Accept': 'application/json',
            },
        )
        if response.status_code > 205:
            raise FetcherError(f"Failed to fetch projects from {__hosting_id__}: {response.text}")
        return response.json()

    def _get_projects_manifest_urls(self) -> Generator[str]:
        manifest_url_list_json = self._download_projects_index()
        for manifest_url in manifest_url_list_json:
            # manifest_url: str = manifest_url
            yield manifest_url

    def fetch_all(self, start_over=True) -> Generator[FetchResult]:
        manifest_urls = list(self._get_projects_manifest_urls())
        manifest_urls.sort()
        # print("#################################")
        # print('\n'.join(project_ids))
        # appro_projs_csv_path = 'appro_projs.csv'
        # import pathlib
        # pathlib.Path(appro_projs_csv_path).write_text('\n'.join(project_ids))
        # print(f"Written '{appro_projs_csv_path}'.")
        # print("#################################")
        # raise SystemExit(56)
        total_projects = len(manifest_urls)

        proj_idx = -1
        last_visited = datetime.now(timezone.utc)
        fetcher_state: _FetcherState = _FetcherState.load(self._state_repository, start_over=start_over)
        fetcher_state.total_projects = total_projects
        fetcher_state.store(self._state_repository)
        for manifest_url in manifest_urls:
            proj_idx += 1
            log.debug("Fetching project %d/%d", proj_idx, total_projects)

            # try:
            fetch_result = self.__fetch_one_raw(fetcher_state, None, manifest_url, last_visited)
            # except FetcherError as err:
            #     log.warn(f"Failed to fetch project '{hosting_unit_id}': {err}")
            #     continue
            fetcher_state.store(self._state_repository)  # XXX This might be very costly

            yield fetch_result

        self._state_repository.delete(__hosting_id__)
        log.debug(f"fetched {total_projects} projects from {__hosting_id__}")
