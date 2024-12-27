from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from time import sleep

import requests
from gql import Client as GQLClient
from gql import gql
from gql.transport.exceptions import TransportAlreadyConnected
from gql.transport.requests import RequestsHTTPTransport
from requests.adapters import HTTPAdapter, Retry

from krawl.config import Config
from krawl.errors import FetcherError, NotFound, ParserError
from krawl.fetcher import Fetcher
from krawl.fetcher.event import FailedFetch
from krawl.fetcher.result import FetchResult
from krawl.fetcher.util import is_accepted_manifest_file_name, is_empty
from krawl.log import get_child_logger
from krawl.model.agent import Organization
from krawl.model.data_set import CrawlingMeta, DataSet
from krawl.model.hosting_id import HostingId
from krawl.model.hosting_unit import HostingUnitIdForge
from krawl.model.licenses import License
from krawl.model.licenses import get_by_id_or_name_required as get_license_required
from krawl.model.manifest import Manifest, ManifestFormat
# from krawl.model.project import Project
from krawl.model.project_id import ProjectId
from krawl.model.sourcing_procedure import SourcingProcedure
from krawl.normalizer import Normalizer
from krawl.normalizer.github import GitHubFileHandler
from krawl.normalizer.manifest import ManifestNormalizer
from krawl.repository import FetcherStateRepository
from krawl.request.rate_limit import RateLimitFixedTimedelta, RateLimitNumRequests

__long_name__: str = "github"
__hosting_id__: HostingId = HostingId.GITHUB_COM
__sourcing_procedure__: SourcingProcedure = SourcingProcedure.MANIFEST
log = get_child_logger(__long_name__)

MANIFEST_FILE_EXTENSIONS = ['toml', 'yaml', 'yml', 'json', 'ttl', 'rdf', 'jsonld']
#pylint: disable=consider-using-f-string
RATELIMIT_FIELDS = """
rateLimit {
    limit     # maximum budget resets every hour
    cost      # cost of this query
    remaining # remaining budget
    resetAt   # UTC time until budget reset
}
"""
PROJECT_FIELDS = """
owner {
    login
}
name
isInOrganization
url
description
createdAt
updatedAt
defaultBranchRef {
  name
}
latestRelease {
    tag {
        name
    }
}
licenseInfo {
    spdxId
}
repositoryTopics(first: 10) {
    nodes {
        topic {
            name
        }
    }
}
isArchived
forkCount
stargazerCount
"""
QUERY_PROJECTS = gql("""
query ($batchSize: Int!, $cursor: String!) {
    repositories(first: $batchSize, after: $cursor, privacy: PUBLIC) {
        result {
            pageInfo {
                hasNextPage
                endCursor
            }
            edges {
                node {
                    %s
                }
            }
        }
    }
    %s
}
""" % (PROJECT_FIELDS, RATELIMIT_FIELDS))
QUERY_PROJECT = gql("""
query ($owner: String!, $name: String!) {
    repository(owner: $owner, name: $name) {
        %s
    }
    %s
}
""" % (PROJECT_FIELDS, RATELIMIT_FIELDS))
#pylint: enable=consider-using-f-string


class GitHubFetcher(Fetcher):
    """Fetcher for projects on GitHub.com.

    ### Finding results

    GitHub hosts more than 100 million repositories (Nov 2018) with a large
    variety of content, such as software source code, websites, hardware
    documentation, research results and more. It is not feasible to check each
    and every repository for hardware projects that feature a OKH-LOSH manifest.
    Therefore, to accelerate the search, the code search feature of GitHub is
    used
    (https://docs.github.com/en/search-github/searching-on-github/searching-code).
    It offers the possibility to find files with certain criteria. Once potential
    manifest files are identified, the fetcher will download these and processes
    them.

    ### Challenges

    Searching for manifest files and downloading them from GitHub poses a couple
    of challenges that need to be addressed. Most of them stem from the rate
    limits that GitHub imposes.

    - The code search feature only returns results for repositories that
      had any activity or popped up in search results within the last year. Long
      existing projects with no activity whatsoever, will therefore not be found. By
      continuously searching for new results, the crawler will hopefully pick-up
      recent projects, and keep an index. This way, the projects will be
      included in the database, even if these won't get any future updates.

    - Using the API, the code search will only return a maximum of 1000 results,
      even if more were found. To get more than 1000 results, the crawler needs
      to split up the search query into time-frames. Using this method, it should
      be possible to get all the results (https://stackoverflow.com/a/37639739).

    - GitHub uses rate limits for all requests made to their API. These need to
      be respected, otherwise the application might get blocked completely. The
      different sets of rate limits can be found here:
        - REST:
          <https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting>
        - GraphQL:
          <https://docs.github.com/en/graphql/overview/resource-limitations#rate-limit>
        - Secondary:
          <https://docs.github.com/en/rest/guides/best-practices-for-integrators#dealing-with-secondary-rate-limits>

    - One of the most annoying limits is the imposed timeout for code search
      queries. When a query exceeds a certain short timeout, only the results
      until this point will be returned. GitHub states, that the response would
      contain the field `incomplete_results` set to `true`, but it seems not to
      work
      (https://docs.github.com/en/rest/reference/search#timeouts-and-incomplete-results).
      The latter doesn't really matter, because it wouldn't help to get the
      desired results anyway. The concrete problem is the following: Results
      from the code search can only be accessed in a paginated form, meaning only
      up to 100 results can be retrieved in one batch. The next 100 results
      could then be retrieved by querying the next page. Now, the timeout comes
      into play: If 100 results from page X are requested, but for example only
      15 are returned, then there is no way to access the other 75 results of
      that page. Going to the next page would return the results 100-200. To
      counter this, one could do the following:
        - simple search query: The more complex the search query is, the more
          processing is required and the query will take longer. Therefore, the
          query needs to be kept simple, even if this means, that the search is
          less specific and returns overall more results. Here is an example,
          that I first used for querying:

            `okhv filename:okh extension:toml extension:yaml extension:yml size:<=384000`

          This query searches for the string `okhv` inside files, which have one
          of the extensions `toml`, `yaml` or `yml` and also a maximum size of
          384000 bytes. The size of searchable files is limited by GitHub to 384
          KB anyway, so that part can be removed. The search for file content is
          especially computational expensive, which is why it should be removed
          from the query. The simplified query would then be:

            `filename:okh extension:toml extension:yaml extension:yml`

        - small batch size: The more results are requested per page, the
          likelier it is, that the timeout will cut off the returned results.
          Therefore, the batch size needs to be kept small. A batch size of
          10 might be reasonable.

        - retry: Because the missing results cannot be requested properly, we
          have to run the query again, and hope that the next time all the
          expected results show up.

    ### Development Information

    GitHub offers a GraphQL API that is used by the fetcher to get all projects
    and their metadata. For developing the query, one can use the in-browser tool
    available at https://docs.github.com/en/graphql/overview/explorer. To debug
    the query, simply post it into the tool along with the following variables:

        {
            "batchSize": 2,
            "cursor": ""
        }

    The full public schema is available at:
    https://docs.github.com/public/schema.docs.graphql

    More information can be found in the official API documentation:
    https://docs.github.com/en/graphql
    """

    HOSTING_ID: HostingId = __hosting_id__
    RETRY_CODES = [429, 500, 502, 503, 504]
    BATCH_SIZE = 10
    CONFIG_SCHEMA = Fetcher._generate_config_schema(long_name=__long_name__, default_timeout=15, access_token=True)

    def __init__(self, state_repository: FetcherStateRepository, config: Config) -> None:
        super().__init__(state_repository=state_repository)
        # self._state_repository = state_repository
        # self._normalizer = self.create_normalizer()
        # self._deserializer_factory = DeserializerFactory()
        self._repo_cache: dict[str, dict] = {}
        # https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting
        self._primary_search_rate_limit = RateLimitNumRequests(num_requests=30)
        # https://docs.github.com/en/graphql/overview/resource-limitations#rate-limit
        self._primary_repo_rate_limit = RateLimitNumRequests(num_requests=5000)
        # https://docs.github.com/en/rest/guides/best-practices-for-integrators#dealing-with-secondary-rate-limits
        self._secondary_rate_limit = RateLimitFixedTimedelta(seconds=5)
        self._file_rate_limit = RateLimitFixedTimedelta(seconds=1)

        retry = Retry(
            total=config.retries,
            backoff_factor=30,
            status_forcelist=self.RETRY_CODES,
        )

        # client for GraphQL requests
        self._transport = RequestsHTTPTransportRetries(
            url="https://api.github.com/graphql",
            headers={
                "User-Agent": config.user_agent,
                "Authorization": f"bearer {config.access_token}",
            },
            verify=True,
            retries=retry,
            timeout=config.timeout,
        )
        self._graphql_client = GQLClient(
            transport=self._transport,
            fetch_schema_from_transport=False,
        )

        # client REST requests (used because the GraphQL API doesn't support code searches)
        self._session = requests.Session()
        self._session.mount(
            "https://",
            HTTPAdapter(max_retries=retry),
        )
        self._session.headers.update({
            "User-Agent": config.user_agent,
            "Authorization": f"token {config.access_token}",
        })

    @classmethod
    def create_normalizer(cls) -> Normalizer:
        return ManifestNormalizer(GitHubFileHandler())

    def __fetch_one(self, hosting_unit_id: HostingUnitIdForge, path: Path) -> FetchResult:
        try:
            log.debug("fetching project '%s' path '%s' ...", hosting_unit_id, str(path))

            # check file name
            if not is_accepted_manifest_file_name(path):
                raise FetcherError(f"Not an accepted manifest file name: '{path.name}'")

            # download the file
            # hosting_unit_id = self._edit_hosting_unit_id(hosting_unit_id)
            # NOTE For some reason, Andre once decided to only download from the default branch,
            #      as documented inside `self._edit_hosting_unit_id()`.
            #      The reason why though, is not given,
            #      so I decided not to update the `hosting_unit_id` here.
            #      Yet, I still call the function, to do magic with the rate limits,
            #      even though I am not sure that is necessary.
            _hosting_unit_id = self._edit_hosting_unit_id(hosting_unit_id)
            manifest_dl_url = hosting_unit_id.create_download_url(path)
            last_visited = datetime.now(timezone.utc)
            manifest_contents = self._download_manifest(manifest_dl_url)

            # check file contents
            if is_empty(manifest_contents):
                raise FetcherError(f"Manifest file is empty: '{manifest_dl_url}'")
            # if is_binary(manifest_contents):
            #     raise FetcherError(f"Manifest file is binary (should be text): '{manifest_dl_url}'")

            format_suffix = path.suffix.lower().lstrip('.')
            manifest_format: ManifestFormat = ManifestFormat.from_ext(format_suffix)
            manifest = Manifest(content=manifest_contents, format=manifest_format)

            # is_yaml = format_suffix in ['yml', 'yaml']
            # log.debug(f"Checking if manifest '{format_suffix}' is YAML ...")
            # if is_yaml:
            #     log.debug("Manifest is YAML!")
            #     try:
            #         manifest_contents = convert_okh_v1_to_losh(manifest_contents)
            #     except ConversionError as err:
            #         raise FetcherError(f"Failed to convert YAML (v1) Manifest to TOML (LOSH): {err}") from err
            #     format_suffix = ".toml"
            #     log.debug("YAML (v1) Manifest converted to TOML (LOSH)!")

            data_set = DataSet(
                okhv="OKH-LOSHv1.0",  # FIXME Not good, not right
                crawling_meta=CrawlingMeta(
                    sourcing_procedure=__sourcing_procedure__,
                    # created_at: datetime = None
                    last_visited=last_visited,
                    manifest=str(path),
                    # last_changed: datetime = None
                    # history = None,
                ),
                hosting_unit_id=hosting_unit_id,
                license=None,  # TODO,
                creator=None,  # TODO,
            )
            # log.info(f"manifest_contents: {manifest_contents}")

            # # try deserialize
            # try:
            #     project = self._deserializer_factory.deserialize(format_suffix, manifest_contents, self._normalizer,
            #                                                      unfiltered_output)
            # except DeserializerError as err:
            #     raise FetcherError(
            #         f"deserialization failed (invalid content/format for its file-type): {err}") from err
            # except NormalizerError as err:
            #     raise FetcherError(f"normalization failed: {err}") from err

            log.debug("fetched project %s", hosting_unit_id)
            fetch_result = FetchResult(data_set=data_set, data=manifest)

            self._fetched(fetch_result)
            return fetch_result
        except FetcherError as err:
            self._failed_fetch(FailedFetch(hosting_unit_id=hosting_unit_id, error=err))
            raise err

    def fetch(self, project_id: ProjectId) -> FetchResult:
        try:
            hosting_unit_id, path_raw = HostingUnitIdForge.from_url(project_id.uri)
        except ParserError as err:
            raise FetcherError(f"Invalid GitHub manifest file URL: '{project_id.uri}'") from err

        if path_raw:
            path = Path(path_raw)
            return self.__fetch_one(hosting_unit_id, path)

        for man_fl_ext in MANIFEST_FILE_EXTENSIONS:
            path = Path(f'okh.{man_fl_ext}')
            try:
                return self.__fetch_one(hosting_unit_id, path)
            except FetcherError:
                continue
        raise FetcherError("Non direct path to a manifest file given,"
                           f" and no known manifest file found at: '{project_id.uri}'")

    def fetch_all(self, start_over=True) -> Generator[FetchResult]:
        num_fetched_projects: int = 0
        if start_over:
            self._state_repository.delete(__hosting_id__)
        else:
            state = self._state_repository.load(__hosting_id__)
            if state:
                num_fetched_projects = state.get("num_fetched_projects", 0)

        num_retries_after_incomplete_results = 0
        page = (num_fetched_projects // self.BATCH_SIZE) + 1
        while True:
            log.debug("fetching projects %d to %d", num_fetched_projects, num_fetched_projects + self.BATCH_SIZE)

            # apply rate limits
            self._primary_search_rate_limit.apply()
            self._secondary_rate_limit.apply()

            # use code search to find files that might be OKH-LOSH manifests
            headers = {
                "Accept": "application/vnd.github.v3+json",
            }
            query = {
                "q": "filename:okh extension:toml extension:yaml extension:yml",
                # "q": "path:/(^|\\/)okh(-[0-9a-zA-Z._-]+)\\.(ya?ml|toml|json(ld)?|ttl)$/",
                # "q": "path:/okh.*yml/",
                # "q": "path:okh.yml",
                # "q": "path:okh.toml",
                "per_page": self.BATCH_SIZE,
                "page": page,
            }
            # code search is not available in the GitHub API v4 (graphql)
            # information on code search: https://docs.github.com/en/rest/reference/search
            # TODO: code search only returns a maximum of 1000 files -> need another method of finding manifest files
            # https://github.com/PyGithub/PyGithub/issues/824#issuecomment-398942171
            response = self._session.get(
                url="https://api.github.com/search/code",
                headers=headers,
                params=query,
            )
            self._secondary_rate_limit.update()

            match response.status_code:
                case 403:
                    message = response.json().get("message", "")
                    if "rate limit" in message:
                        seconds = 60
                        log.debug("hit secondary rate limit, now waiting %d seconds...", seconds)
                        sleep(seconds)
                        continue  # restart loop
                    raise FetcherError(
                        f"failed to fetch projects from GitHub (HTTP Response: {response.status_code}): {response.text}"
                    )
                case 200:
                    pass
                case _:
                    raise FetcherError(
                        f"failed to fetch projects from GitHub (HTTP Response: {response.status_code}): {response.text}"
                    )

            # parse response data
            response_data = response.json()
            self._primary_search_rate_limit.update(
                num_requests=int(response.headers["X-RateLimit-Remaining"]),
                reset_time=datetime.fromtimestamp(int(response.headers["X-RateLimit-Reset"]), tz=timezone.utc),
            )

            # Retrieve the files from the list of results and check if the
            # results are actually complete. See description at the top of the
            # class for an explanation why.
            total_count = response_data.get("total_count", 0)
            raw_found_files = response_data.get("items", [])
            log.debug(f"found files: {total_count}")
            # for raw_found_file in raw_found_files:
            #     raw_url = urlparse(raw_found_file["html_url"])
            #     log.debug(f"    found file: '{raw_url}'")
            is_last_page = page * self.BATCH_SIZE >= total_count
            expected_num_results = self.BATCH_SIZE if not is_last_page else total_count % self.BATCH_SIZE
            if len(raw_found_files) < expected_num_results:
                if num_retries_after_incomplete_results >= 10:
                    raise FetcherError("failed to fetch complete set of results, "
                                       f"got only {num_fetched_projects}/{expected_num_results} from page {page}")
                log.debug("got incomplete set of results, retrying...")
                num_retries_after_incomplete_results = num_retries_after_incomplete_results + 1
                continue
            num_retries_after_incomplete_results = 0

            # figure out what the links are in the default repo -> accessible later on
            for raw_found_file in raw_found_files:
                raw_url = raw_found_file["html_url"]
                # parsed_url = urlparse(raw_url)
                hosting_id, path = HostingUnitIdForge.from_url(raw_url)
                # path = Path(raw_url.path)
                # path_parts = path.parts
                # owner = path_parts[1]
                # repo = path_parts[2]
                # ref = str(Path(*path_parts[5:]))
                # id = ProjectId(__hosting_id__, path_parts[1], path_parts[2], str(Path(*path_parts[5:])))
                # hosting_id = HostingUnitIdForge(
                #     _hosting_id=__hosting_id__,
                #     owner=owner,
                #     repo=repo,
                #     ref=ref,
                # )

                try:
                    yield self.__fetch_one(hosting_id, path)
                except FetcherError as err:
                    log.debug(f"skipping file, because: {err}")

            # save current progress
            page = page + 1
            num_fetched_projects = num_fetched_projects + len(raw_found_files)
            self._state_repository.store(__hosting_id__, {
                "num_fetched_projects": num_fetched_projects,
            })

            if is_last_page:
                break

        self._state_repository.delete(__hosting_id__)
        log.debug("fetched %d projects from GitHub", num_fetched_projects)

    def _edit_hosting_unit_id(self, hosting_unit_id: HostingUnitIdForge) -> HostingUnitIdForge:
        # NOTE This updates rate limits!
        cached_repo = self._get_repo_info(hosting_unit_id)
        default_branch = cached_repo["defaultBranchRef"]["name"]
        # we only consider the default branch, when downloading files
        return hosting_unit_id.derive(ref=default_branch)

    def _download_manifest(self, url) -> bytes:
        self._file_rate_limit.apply()
        log.debug("downloading manifest file %s", url)
        response = self._session.get(url)
        self._file_rate_limit.update()
        match response.status_code:
            case 200:
                pass
            case _:
                err_desc = '(=> does not exist) ' if response.status_code == 404 else ''
                raise NotFound("Tried to download manifest, but failed with HTTP status code"
                               f" {response.status_code}{err_desc} here: '{url}'")

        return response.content

    def _get_repo_info(self, hosting_unit_id: HostingUnitIdForge) -> dict:
        # return cached information
        key = str(hosting_unit_id)
        if key in self._repo_cache:
            return self._repo_cache[key]

        # apply rate limits
        self._primary_repo_rate_limit.apply()
        self._secondary_rate_limit.apply()

        # get information from GitHub
        log.debug(f"requesting repository information for '{key}'")
        params = {"owner": hosting_unit_id.owner, "name": hosting_unit_id.repo}
        try:
            result = self._graphql_client.execute(QUERY_PROJECT, variable_values=params)
        except Exception as err:
            raise FetcherError(f"failed to fetch GitHub repository information for '{hosting_unit_id}': {err}") from err
        finally:
            self._secondary_rate_limit.update()

        # parse response data
        self._primary_repo_rate_limit.update(
            num_requests=result["rateLimit"]["remaining"],
            reset_time=datetime.strptime(result["rateLimit"]["resetAt"], "%Y-%m-%dT%H:%M:%S%z"),
        )
        self._repo_cache[key] = result["repository"]

        return result["repository"]


class RequestsHTTPTransportRetries(RequestsHTTPTransport):

    def connect(self):
        if self.session is None:
            adapter = HTTPAdapter(max_retries=self.retries)
            self.session = requests.Session()
            for prefix in "http://", "https://":
                self.session.mount(prefix, adapter)
        else:
            raise TransportAlreadyConnected("Transport is already connected")
