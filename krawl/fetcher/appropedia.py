from __future__ import annotations

import re
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

# from krawl.request.rate_limit import RateLimitFixedTimedelta

# from krawl.util import slugify

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
    RETRY_CODES = [429, 500, 502, 503, 504]
    # BATCH_SIZE = 50
    CONFIG_SCHEMA = Fetcher._generate_config_schema(long_name=__long_name__, default_timeout=1, access_token=False)

    def __init__(self, state_repository: FetcherStateRepository, config: Config) -> None:
        super().__init__(state_repository=state_repository)
        # self._rate_limit = RateLimitFixedTimedelta(seconds=5)

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
            # "Authorization": f"Bearer {config.access_token}",
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

    def _download_projects_index(self) -> str:
        response = self._session.get(
            # url="https://www.appropedia.org/Special:Export",
            url="https://www.appropedia.org/Special:Export?catname=Projects",
            headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://www.appropedia.org',
                'Referer': 'https://www.appropedia.org/Special:Export?catname=Projects',
                'Upgrade-Insecure-Requests': '1',
            },
            data={
                'catname': 'Projects',
                'addcat': 'Add',
                'pages': '',
                'curonly': '1',
                'wpDownload': '1',
                'wpEditToken': '5f27bfd18afea6b01388921dcead718d676d9c64+\\',
                'title': 'Special%3AExport'
            },
            # params={
            #     "limit": batch_size,
            #     "offset": last_offset
            # },
        )
        if response.status_code > 205:
            raise FetcherError(f"Failed to fetch projects from {__hosting_id__}: {response.text}")
        return response.text

    def _get_projects_index(self) -> Generator[str]:
        project_list_html = self._download_projects_index()
        # log.debug("Raw fetched project index HTML:\n---\n%s\n---", project_list_html)
        raw_html_file = "appro_raw_proj_index.html"
        with open(raw_html_file, "w") as text_file:
            text_file.write(project_list_html)
        # write_to_file(raw_html_file, project_list_html)
        log.debug("Raw fetched project index HTML written to: '%s'", raw_html_file)

        pat_id = re.compile(r".*id='ooui-php-2'")
        pat_tag_end = re.compile(r".*>")
        pat_tag_start = re.compile(r".*>")

        found_id = False
        in_list = False
        done = False
        for line in project_list_html.splitlines():
            if not found_id:
                changed_line = pat_id.sub("", line)
                if changed_line != line:
                    found_id = True
                    line = changed_line
            if found_id and not in_list and not done:
                changed_line = pat_tag_end.sub("", line)
                if changed_line != line:
                    in_list = True
                    line = changed_line
            was_in_list = in_list
            if in_list:
                new_line = pat_tag_start.sub("", line)
                if new_line != line:
                    in_list = False
                    done = True
            if was_in_list:
                yield line.replace("&amp;", "&").replace("&quot;", "\"")

    def fetch_all(self, start_over=True) -> Generator[FetchResult]:
        # last_offset = 0
        # num_fetched = 0
        # batch_size = self.BATCH_SIZE
        # if start_over:
        #     self._state_repository.delete(__hosting_id__)
        # else:
        #     state = self._state_repository.load(__hosting_id__)
        #     if state:
        #         last_offset = state.get("last_offset", 0)  # TODO
        #         num_fetched = state.get("num_fetched", 0)

        project_ids = list(self._get_projects_index())
        project_ids.sort()
        total_projects = len(project_ids)
        log.debug("All fetched Project IDs:\n---\n%s\n---", "\n".join(project_ids))

        proj_idx = -1
        last_visited = datetime.now(timezone.utc)
        fetcher_state: _FetcherState = _FetcherState.load(self._state_repository)
        fetcher_state.total_projects = total_projects
        fetcher_state.store(self._state_repository)
        for project_id in project_ids:
            proj_idx += 1
            log.debug("Fetching project %d/%d", proj_idx, total_projects)

            hosting_unit_id = HostingUnitIdWebById(_hosting_id=__hosting_id__, project_id=project_id)
            fetch_result = self.__fetch_one(fetcher_state, hosting_unit_id, last_visited)
            fetcher_state.store(self._state_repository)  # XXX This might be very costly

            # manifest_dl_url = f"https://www.appropedia.org/generateOpenKnowHowManifest.php?title={self.url_encode(project_id)}"
            # okh_v1_contents = self._download_manifest(manifest_dl_url)

            # data = response.json()
            # last_visited = datetime.now(timezone.utc)
            # for raw_project in data["items"]:
            #     hosting_unit_id = HostingUnitIdWebById(_hosting_id=__hosting_id__, project_id=raw_project['oshwaUid'])
            #     project = self.__fetch_one(hosting_unit_id, raw_project, last_visited)
            #     log.debug("yield project %s", hosting_unit_id)
            #     yield project

            # # save current progress
            # batch_size = data["limit"]  # in case the batch size will be lowered on the platform in some point in time
            # num_fetched += len(data["items"])
            # last_offset += batch_size
            # if last_offset > data["total"]:
            #     break

            self._state_repository.store(__hosting_id__, {
                "last_offset": proj_idx,
                "num_fetched": proj_idx,
            })

            yield fetch_result

        self._state_repository.delete(__hosting_id__)
        log.debug(f"fetched {total_projects} projects from {__hosting_id__}")
