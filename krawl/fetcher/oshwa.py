from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from krawl.config import Config
from krawl.errors import FetcherError, NormalizerError
from krawl.fetcher import Fetcher
from krawl.log import get_child_logger
from krawl.normalizer.oshwa import OshwaNormalizer
from krawl.project import Project, ProjectID
from krawl.repository import FetcherStateRepository
from krawl.request.rate_limit import RateLimitFixedTimedelta
from krawl.util import slugify

log = get_child_logger("oshwa")


class OshwaFetcher(Fetcher):
    NAME = "oshwa.org"
    RETRY_CODES = [429, 500, 502, 503, 504]
    BATCH_SIZE = 50
    CONFIG_SCHEMA = {
        "type": "dict",
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

    def fetch(self, id: ProjectID) -> Project:

        log.debug('Start fetching project %s', id)

        oshwa_id = id.path.split(".")[0]

        response = self._session.get(
            url=f"https://certificationapi.oshwa.org/api/projects/{oshwa_id}",
        )

        if response.status_code > 205:
            raise FetcherError(f"failed to fetch projects from OSHWA: {response.text}")

        raw_project = response.json()[0]


        last_visited = datetime.now(timezone.utc)

        new_id = ProjectID(self.NAME, slugify(raw_project["responsibleParty"]), raw_project["oshwaUid"].lower())

        meta = {
            "meta": {
                "id": new_id,
                "fetcher": self.NAME,
                "last_visited": last_visited,
            }
        }

        # try normalizing it
        try:
            raw_project.update(meta)
            project = self._normalizer.normalize(raw_project)
        except NormalizerError as err:
            raise FetcherError(f"normalization failed, that should not happen: {err}") from err

        log.debug("yield project %s", project.id)

        return project

    def fetch_all(self, start_over=True) -> Generator[Project, None, None]:
        last_offset = 0
        num_fetched = 0
        batch_size = self.BATCH_SIZE
        if start_over:
            self._state_repository.delete(self.NAME)
        else:
            state = self._state_repository.load(self.NAME)
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
                raise FetcherError(f"failed to fetch projects from OSHWA: {response.text}")

            data = response.json()
            last_visited = datetime.now(timezone.utc)
            for raw_project in data["items"]:
                # create fetcher metadata
                id = ProjectID(self.NAME, slugify(raw_project["responsibleParty"]), raw_project["oshwaUid"].lower())
                meta = {
                    "meta": {
                        "id": id,
                        "fetcher": self.NAME,
                        "last_visited": last_visited,
                    }
                }

                # try normalizing it
                try:
                    raw_project.update(meta)
                    project = self._normalizer.normalize(raw_project)
                except NormalizerError as err:
                    raise FetcherError(f"normalization failed, that should not happen: {err}") from err

                log.debug("yield project %s", project.id)
                yield project

            # save current progress
            batch_size = data["limit"]  # in case the batch size will be lowered on the platform in some point in time
            num_fetched += len(data["items"])
            last_offset += batch_size
            if last_offset > data["total"]:
                break

            self._state_repository.store(self.NAME, {
                "last_offset": last_offset,
                "num_fetched": num_fetched,
            })

        self._state_repository.delete(self.NAME)
        log.debug("fetched %d projects from OSHWA", num_fetched)
