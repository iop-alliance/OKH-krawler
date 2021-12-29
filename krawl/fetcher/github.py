from __future__ import annotations

import logging
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import sleep
from urllib.parse import urlparse, urlunparse

import requests
from gql import Client as GQLClient
from gql import gql
from gql.transport.exceptions import TransportAlreadyConnected
from gql.transport.requests import RequestsHTTPTransport
from requests.adapters import HTTPAdapter, Retry
from requests.auth import HTTPBasicAuth

from krawl.config import Config
from krawl.exceptions import FetchingException, NotAManifest, NotFound
from krawl.fetcher import Fetcher
from krawl.fetcher.util import parse_manifest
from krawl.normalizer.manifest import ManifestNormalizer
from krawl.project import Project, ProjectID
from krawl.repository import FetcherStateRepository

log = logging.getLogger("github-fetcher")

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

    GitHub offers a GraphQL API, that is used by the fetcher to get all projects
    and their metadata. For developing the query one can use the in-browser tool
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
    CONFIG_SCHEMA = {
        "type": "dict",
        "default": {},
        "meta": {
            "long_name": "github",
        },
        "schema": {
            "batch_size": {
                "type": "integer",
                "default": 50,
                "min": 1,
                # the documentation says the max value is 100, but beyond 50 I seem to get random number of results
                # https://docs.github.com/en/rest/reference/search#search-code
                "max": 50,
                "meta": {
                    # used in CLI
                    "long_name": "batch-size",
                    "description": "Number of requests to perform at a time"
                }
            },
            "timeout": {
                "type": "integer",
                "default": 10,
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
        self._batch_size = config.batch_size
        self._normalizer = ManifestNormalizer()
        self._repo_cache = {}
        self._rate_limit = {}

        retry = Retry(
            total=config.retries,
            backoff_factor=15,
            status_forcelist=self.RETRY_CODES,
        )

        # client for GRAPHQL requests
        self._transport = RequestsHTTPTransportRetries(
            url="https://api.github.com/graphql",
            headers={
                "User-Agent": "OKH-LOSH-Crawler github.com/OPEN-NEXT/OKH-LOSH",  #FIXME: use user agent defined in config
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

        # client REST requests (used because the GRAPHQL API doesn't support code searches)
        self._session = requests.Session()
        self._session.mount(
            "https://",
            HTTPAdapter(max_retries=retry),
        )
        self._session.headers.update({
            "User-Agent": "OKH-LOSH-Crawler github.com/OPEN-NEXT/OKH-LOSH",  #FIXME: use user agent defined in config
            "Authorization": f"token {config.access_token}",
        })

    def fetch(self, id: ProjectID) -> Project:
        log.debug("fetching project %s", id)

        # download manifest file
        manifest_contents = self._download_manifest(id)
        manifest = parse_manifest(manifest_contents, Path(id.path).suffix)

        # enrich result
        raw = {
            "manifest": manifest,
            "owner": id.owner,
            "repo": id.repo,
            "path": id.path,
            "fetcher": self.NAME,
            "last_visited": datetime.now(timezone.utc),
        }
        return self._normalizer.normalize(raw)

    def fetch_all(self, start_over=True) -> Generator[Project, None, None]:
        num_fetched_projects = 0
        if start_over:
            self._state_repository.delete(self.NAME)
        else:
            state = self._state_repository.load(self.NAME)
            if state:
                num_fetched_projects = state.get("num_fetched_projects", 0)

        page = (num_fetched_projects // self._batch_size) + 1
        last_api_request = datetime(1, 1, 1, 0, 0, tzinfo=timezone.utc)
        rate_limit_remaining = 1
        rate_limit_reset = datetime(1, 1, 1, 0, 0, tzinfo=timezone.utc)
        while True:
            log.debug("fetching projects %d to %d", num_fetched_projects, num_fetched_projects + self._batch_size)

            # primary rate limits
            # https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting
            if rate_limit_remaining == 0:
                seconds = (rate_limit_reset - datetime.now(timezone.utc)).seconds
                log.info("hit primary rate limit, now waiting %d seconds...", seconds)
                sleep(seconds)

            # secondary rate limits
            # https://docs.github.com/en/rest/guides/best-practices-for-integrators#dealing-with-secondary-rate-limits
            if (datetime.now(timezone.utc) - last_api_request) < timedelta(seconds=1):
                log.debug("trying to avoid secondary rate limit by waiting one second...")
                sleep(1)

            # use code search to find files that might be OKH-LOSH manifests
            headers = {
                "Accept": "application/vnd.github.v3+json",
            }
            query = {
                "q": "okhv filename:okh extension:toml extension:yaml extension:yml size:<=384000",
                # in theory it is possible to request up to 100 results per
                # page, but the due to exceeding a query timeout the result set
                # will likely be smaller than what was requested
                # (https://docs.github.com/en/rest/reference/search#timeouts-and-incomplete-results).
                # GitHub says it will inform if a timeout occurs by setting
                # `incomplete_results` to `true`, but it doesn't. Anyway, there
                # is no good solution for getting the missing results. One could
                # change the results per page and figure out a page number, that
                # would include the missing results, but this is cumbersome.
                "per_page": self._batch_size,
                "page": page,
            }
            # code search is not available in the GitHub API v4 (graphql)
            # information on code search: https://docs.github.com/en/rest/reference/search
            # TODO: code search only returns a maximum of 1000 files -> need another method of finding manifest files
            response = self._session.get(
                url="https://api.github.com/search/code",
                headers=headers,
                params=query,
            )

            if response.status_code == 403:
                message = response.json().get("message", "")
                if "rate limit" in message:
                    seconds = 60
                    log.debug("hit secondary rate limit, now waiting %d seconds...", seconds)
                    sleep(seconds)
                    continue
            elif response.status_code != 200:
                raise FetchingException(f"failed to fetch projects from GitHub: {response.text}")
            response_data = response.json()
            raw_found_files = response_data.get("items", [])
            # is_last_page = response_data.get("total_count")
            if not raw_found_files:
                break

            page = page + 1
            num_fetched_projects = num_fetched_projects + len(raw_found_files)

            # primary rate limit
            rate_limit_remaining = int(response.headers["X-RateLimit-Remaining"])
            rate_limit_reset = datetime.fromtimestamp(int(response.headers["X-RateLimit-Reset"]), tz=timezone.utc)

            # figure out what the links are in the default repo -> accessable later on
            last_visited = datetime.now(timezone.utc)
            for raw_found_file in raw_found_files:
                raw_url = urlparse(raw_found_file["html_url"])
                path_parts = Path(raw_url.path).parts
                # create ID and use that for downloading the file
                id = ProjectID(self.NAME, path_parts[1], path_parts[2], str(Path(*path_parts[5:])))

                # download manifest file
                manifest_contents = self._download_manifest(id)
                try:
                    manifest = parse_manifest(manifest_contents, Path(id.path).suffix)
                except NotAManifest:
                    # not a valid manifest -> skip
                    log.debug("skipping project, because it is not a manifest (%s)", id)
                    continue

                # enrich result
                raw = {
                    "manifest": manifest,
                    "owner": id.owner,
                    "repo": id.repo,
                    "path": id.path,
                    "fetcher": self.NAME,
                    "last_visited": last_visited,
                }
                project = self._normalizer.normalize(raw)
                log.debug("yield project %s", project.id)
                yield project

            # save current progress
            self._state_repository.store(self.NAME, {
                "num_fetched_projects": num_fetched_projects,
            })

        self._state_repository.delete(self.NAME)
        log.debug("fetched %d projects from GitHub", num_fetched_projects)

    def _download_manifest(self, id: ProjectID) -> bytes:
        # get repository information
        raw_repo = self._get_repo_info(id)
        default_branch = raw_repo["defaultBranchRef"]["name"]

        # create a download URL in form of: https://raw.githubusercontent.com/owner/name/default_branch/path
        # we only consider the default branch, when downloading files
        download_url = urlunparse((
            "https",
            "raw.githubusercontent.com",
            f"/{id.owner}/{id.repo}/{default_branch}/{id.path}",
            None,
            None,
            None,
        ))

        log.debug("downloading manifest file %s", download_url)
        response = self._session.get(download_url)
        if response.status_code == 404:
            raise NotFound("Manifest doesn't exist on default branch ({download_url})")
        elif response.status_code != 200:
            raise FetchingException(f"Failed to download manifest file ({download_url}): {response.text}")

        return response.content

    def _get_repo_info(self, id: ProjectID) -> dict:
        # return cached information
        key = f"{id.platform}/{id.owner}/{id.repo}"
        if key in self._repo_cache:
            return self._repo_cache[key]

        # get information from GitHub
        log.debug("requesting repository information for '%s/%s/%s'", id.platform, id.owner, id.repo)
        params = {"owner": id.owner, "name": id.repo}
        try:
            result = self._graphql_client.execute(QUERY_PROJECT, variable_values=params)
        except Exception as e:
            raise FetchingException(f"failed to fetch GitHub repository information '{id}': {e}") from e
        if not result:
            raise FetchingException(f"project '{id}' not found")
        self._repo_cache[key] = result["repository"]
        self._rate_limit = result["rateLimit"]
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
