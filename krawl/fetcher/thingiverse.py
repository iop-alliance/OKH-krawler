import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Generator

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from krawl.config import Config
from krawl.exceptions import FetchingException
from krawl.fetcher import Fetcher
from krawl.normalizer.thingiverse import ThingiverseNormalizer
from krawl.project import Project, ProjectID
from krawl.repository import FetcherStateRepository

thingiverse_logger = logging.getLogger("Thingiverse-Logger")

thingiverse_logger.setLevel(logging.DEBUG)

caught_licenses = dict()


def catch_license(project_license):
    caught_licenses.update({project_license: project_license})


def print_licenses():
    with open('thingiverse-licenses', 'w') as fout:
        fout.writelines(map(lambda l: f"{l}\n", caught_licenses))


class ThingiverseFetcher(Fetcher):
    NAME = 'thingiverse'
    RETRY_CODES = [429, 500, 502, 503, 504]

    CONFIG_SCHEMA = {

        "type": 'dict',
        "meta": {
            "long_name": "thingiverse",
        },
        "schema": {
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
                    "description": "Personal access token for using the thingiverse API"
                }
            },
        },
    }

    def __init__(self, state_repository: FetcherStateRepository, config: Config) -> None:

        self._state_repository = state_repository
        self._normalizer = ThingiverseNormalizer()

        self._repo_cache = {}
        self._rate_limit = {}

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
            "User-Agent": "OKH-LOSH-Crawler github.com/OPEN-NEXT/OKH-LOSH",  # FIXME: use user agent defined in config
            "Authorization": f"Bearer {config.access_token}",
        })

    def fetch(self, id: ProjectID) -> Project:
        pass

    def fetch_all(self, start_over=True) -> Generator[Project, None, None]:

        has_more = True
        page = 1
        projects_counter = 0
        fetched_projects = dict()

        if start_over:
            self._state_repository.delete(self.NAME)
        else:
            state = self._state_repository.load(self.NAME)
            if state:
                page = state.get("page", 1)
                fetched_projects = state.get("fetched_projects", dict())

        # the approach
        #
        # * at the moment the search of thingiverse does not work for any license bug?
        # * limit of 10000 hits
        # * the search results dont have all need information
        # * we need to query every project to obtain the description,

        while has_more:

            response = self._session.get(
                url="https://api.thingiverse.com/search/",
                params={"page": page, "type": "things"},
            )

            if response.status_code > 205:
                raise FetchingException(f"failed to fetch projects from Thingiverse: {response.text}")

            data = response.json()

            pages = math.ceil(data['total'] / 10)

            if pages > page:
                page += 1
                has_more = False  # TODO  remove
            else:
                has_more = False

            last_visited = datetime.now(timezone.utc)

            for item in data['hits']:

                if item['id'] in fetched_projects:
                    if fetched_projects[item['id']] > last_visited.timestamp() - timedelta(days=30).total_seconds():
                        thingiverse_logger.info('Skipping: Project already fetched')
                        continue

                projects_counter += 1
                thingiverse_logger.info(f"Convert item {item.get('name')}..")

                item['lastVisited'] = last_visited
                item["fetcher"] = self.NAME

                single_project = self._fetch_raw(item['id'])
                complete_project = {**item, **single_project}

                project = self._normalizer.normalize(complete_project)
                if not project:
                    thingiverse_logger.warning("project with name %s could not be normalized", complete_project['name'])
                    continue

                catch_license(single_project['license'])
                thingiverse_logger.debug("%d yield project %s", projects_counter, project.id)
                print_licenses()
                fetched_projects.update({item['id']: last_visited.timestamp()})
                yield project

            # save current progress
            self._state_repository.store(self.NAME, {
                "page": page,
                "fetched_projects": fetched_projects
            })

        # self._state_repository.delete(self.NAME)

    def _fetch_raw(self, thingiverse_id: str) -> dict:

        response = self._session.get(
            url=f"https://api.thingiverse.com/things/{thingiverse_id}",
        )

        if response.status_code > 205:
            raise FetchingException(f"failed to fetch project from Thingiverse: {response.text}")

        return response.json()
