import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from krawl.config import Config
from krawl.exceptions import FetchingException
from krawl.fetcher import Fetcher
from krawl.normalizer.oshwa import OshwaNormalizer
from krawl.project import Project, ProjectID
from krawl.repository import FetcherStateRepository

oshwa_logger = logging.getLogger("OSHWA-Logger")
oshwa_logger.setLevel(logging.DEBUG)


class OshwaFetcher(Fetcher):
    NAME = 'OSHWA'
    RETRY_CODES = [429, 500, 502, 503, 504]

    CONFIG_SCHEMA = {
        "type": 'dict',
        "meta": {
            "long_name": "oshwa",
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
                    "description": "Personal access token for using the OSHWAS API"
                }
            },
        },
    }

    def __init__(self, state_repository: FetcherStateRepository, config: Config) -> None:

        self._state_repository = state_repository
        self._normalizer = OshwaNormalizer()

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

        offset = 0
        has_more = True
        page = 1

        while has_more:

            response = self._session.get(
                url="https://certificationapi.oshwa.org/api/projects",
                params={'limit': 1000, 'offset': offset},
            )

            if response.status_code > 205:
                raise FetchingException(f"failed to fetch projects from GitHub: {response.text}")

            data = response.json()

            pages = math.ceil(data['total'] / data['limit'])

            if pages > page:
                offset += 1000
            else:
                has_more = False

            last_visited = datetime.now(timezone.utc)

            for item in data['items']:
                oshwa_logger.info(f"Convert item {item.get('projectName')}..")

                item['lastVisited'] = last_visited
                item["fetcher"] = self.NAME

                project = self._normalizer.normalize(item)

                if project is None:
                    continue

                oshwa_logger.debug("yield project %s", project.id)
                yield project
