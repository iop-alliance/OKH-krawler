from __future__ import annotations

import re
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from time import sleep
from urllib.parse import urlparse, urlunparse

import requests
from gql import Client as GQLClient
from gql import gql
from gql.transport.exceptions import TransportAlreadyConnected
from gql.transport.requests import RequestsHTTPTransport
from requests.adapters import HTTPAdapter, Retry

from krawl.config import Config
from krawl.errors import ConversionError, DeserializerError, FetcherError, NormalizerError, NotFound
from krawl.fetcher import Fetcher
from krawl.fetcher.util import convert_okh_v1_to_losh, is_accepted_manifest_file_name, is_binary, is_empty
from krawl.log import get_child_logger
from krawl.normalizer.github import GitHubFileHandler
from krawl.normalizer.manifest import ManifestNormalizer
from krawl.project import Project, ProjectID
from krawl.repository import FetcherStateRepository
from krawl.request.rate_limit import RateLimitFixedTimedelta, RateLimitNumRequests
from krawl.serializer.factory import DeserializerFactory

log = get_child_logger("github")

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
        - REST: https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting
        - GraphQL: https://docs.github.com/en/graphql/overview/resource-limitations#rate-limit
        - Secondary: https://docs.github.com/en/rest/guides/best-practices-for-integrators#dealing-with-secondary-rate-limits

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

    NAME = "github.com"
    RETRY_CODES = [429, 500, 502, 503, 504]
    BATCH_SIZE = 10
    CONFIG_SCHEMA = {
        "type": "dict",
        "default": {},
        "meta": {
            "long_name": "github",
        },
        "schema": {
            "timeout": {
                "type": "integer",
                "default": 15,
                "min": 1,
                "meta": {
                    "long_name": "timeout",
                    "description": "Max seconds to wait for a not responding service"
                }
            },
            "retries": {
                "type": "integer",
                "default": 3,
                "min": 0,
                "meta": {
                    "long_name": "retries",
                    "description": "Number of retries of requests in cases of network errors"
                }
            },
            "access_token": {
                "type": "string",
                "coerce": "strip_str",
                "required": True,
                "nullable": False,
                "meta": {
                    "long_name": "access-token",
                    "description": "Personal access token for using the GitHub API"
                }
            },
        },
    }

    def __init__(self, state_repository: FetcherStateRepository, config: Config) -> None:
        self._state_repository = state_repository
        self._normalizer = ManifestNormalizer(GitHubFileHandler())
        self._deserializer_factory = DeserializerFactory()
        self._repo_cache = {}
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

    def __fetch_one(self, id: ProjectID, path: Path, last_visited: datetime) -> Project:
        log.debug("fetching project %s ...", id)

        format_suffix = path.suffix.lower()

        # check file name
        if not is_accepted_manifest_file_name(path):
            raise FetcherError(f"Not an accepted manifest file name: '{path}'")

        # download the file
        base_download_url = self._get_file_base_url(id)
        manifest_contents = self._download_manifest(f"{base_download_url}/{id.path}")

        # check file contents
        if is_empty(manifest_contents):
            raise FetcherError(f"Manifest file is empty: '{id}'")
        if is_binary(manifest_contents):
            raise FetcherError(f"Manifest file is binary (should be text): '{id}'")

        yaml_suffix_pat = re.compile('^\\.ya?ml$')
        is_yaml = yaml_suffix_pat.match(format_suffix)
        log.debug(f"Checking if manifest '{format_suffix}' is YAML ...")
        if is_yaml:
            log.debug(f"Manifest is YAML!")
            try:
                manifest_contents = convert_okh_v1_to_losh(manifest_contents)
            except ConversionError as err:
                raise FetcherError(f"Failed to convert YAML (v1) Manifest to TOML (LOSH): {err}") from err
            format_suffix = ".toml"
            log.debug(f"YAML (v1) Manifest converted to TOML (LOSH)!")

        # create fetcher meta data
        meta = {
            "meta": {
                "owner": id.owner,
                "repo": id.repo,
                "path": id.path,
                "fetcher": self.NAME,
                "last_visited": last_visited,
            }
        }

        # try deserialize
        try:
            project = self._deserializer_factory.deserialize(format_suffix, manifest_contents, self._normalizer, meta)
        except DeserializerError as err:
            raise FetcherError(f"deserialization failed (invalid content/format for its file-type): {err}") from err
        except NormalizerError as err:
            raise FetcherError(f"normalization failed: {err}") from err

        log.debug("fetched project %s", project.id)
        return project

    def fetch(self, id: ProjectID) -> Project:
        if id.path is None:
            id.path = 'okh.toml'
        last_visited = datetime.now(timezone.utc)
        path = Path(id.path)

        return self.__fetch_one(id, path, last_visited)

    def fetch_all(self, start_over=True) -> Generator[Project, None, None]:
        num_fetched_projects = 0
        if start_over:
            self._state_repository.delete(self.NAME)
        else:
            state = self._state_repository.load(self.NAME)
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

            if response.status_code == 403:
                message = response.json().get("message", "")
                if "rate limit" in message:
                    seconds = 60
                    log.debug("hit secondary rate limit, now waiting %d seconds...", seconds)
                    sleep(seconds)
                    continue  # restart loop
                raise FetcherError(
                    f"failed to fetch projects from GitHub (HTTP Response: {response.status_code}): {response.text}")
            elif response.status_code != 200:
                raise FetcherError(
                    f"failed to fetch projects from GitHub (HTTP Response: {response.status_code}): {response.text}")

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
            is_last_page = page * self.BATCH_SIZE >= total_count
            expected_num_results = self.BATCH_SIZE if not is_last_page else total_count % self.BATCH_SIZE
            if len(raw_found_files) < expected_num_results:
                if num_retries_after_incomplete_results >= 10:
                    raise FetcherError("failed to fetch complete set of results, "
                                       f"got only {len(num_fetched_projects)}/{expected_num_results} from page {page}")
                log.debug("got incomplete set of results, retrying...")
                num_retries_after_incomplete_results = num_retries_after_incomplete_results + 1
                continue
            num_retries_after_incomplete_results = 0

            # figure out what the links are in the default repo -> accessible later on
            last_visited = datetime.now(timezone.utc)
            for raw_found_file in raw_found_files:
                raw_url = urlparse(raw_found_file["html_url"])
                path = Path(raw_url.path)
                path_parts = path.parts
                id = ProjectID(self.NAME, path_parts[1], path_parts[2], str(Path(*path_parts[5:])))

                try:
                    yield self.__fetch_one(id, path, last_visited)
                except FetcherError as err:
                    log.debug(f"skipping file, because: {err}")

            # save current progress
            page = page + 1
            num_fetched_projects = num_fetched_projects + len(raw_found_files)
            self._state_repository.store(self.NAME, {
                "num_fetched_projects": num_fetched_projects,
            })

            if is_last_page:
                break

        self._state_repository.delete(self.NAME)
        log.debug("fetched %d projects from GitHub", num_fetched_projects)

    def _get_file_base_url(self, id: ProjectID) -> str:
        # get repository information
        raw_repo = self._get_repo_info(id)
        default_branch = raw_repo["defaultBranchRef"]["name"]

        # create a download URL in form of: https://raw.githubusercontent.com/owner/name/default_branch
        # we only consider the default branch, when downloading files
        return urlunparse((
            "https",
            "raw.githubusercontent.com",
            f"/{id.owner}/{id.repo}/{default_branch}",
            None,
            None,
            None,
        ))

    def _download_manifest(self, url) -> bytes:
        self._file_rate_limit.apply()
        log.debug("downloading manifest file %s", url)
        response = self._session.get(url)
        self._file_rate_limit.update()
        if response.status_code == 404:
            raise NotFound(f"Manifest doesn't exist on default branch ({url})")
        elif response.status_code != 200:
            raise FetcherError(f"Failed to download manifest file ({url}): {response.text}")

        return response.content

    def _get_repo_info(self, id: ProjectID) -> dict:
        # return cached information
        key = f"{id.platform}/{id.owner}/{id.repo}"
        if key in self._repo_cache:
            return self._repo_cache[key]

        # apply rate limits
        self._primary_repo_rate_limit.apply()
        self._secondary_rate_limit.apply()

        # get information from GitHub
        log.debug("requesting repository information for '%s/%s/%s'", id.platform, id.owner, id.repo)
        params = {"owner": id.owner, "name": id.repo}
        try:
            result = self._graphql_client.execute(QUERY_PROJECT, variable_values=params)
        except Exception as e:
            raise FetcherError(f"failed to fetch GitHub repository information '{id}': {e}") from e
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
