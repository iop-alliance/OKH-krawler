import logging
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

    def fetch(self, id: ProjectID) -> Project:
        pass

    def fetch_all(self, start_over=True) -> Generator[Project, None, None]:

        offset = 0

        response = self._session.get(
            url="https://certificationapi.oshwa.org/api/projects",
            params={'limit': 1000, 'offset': offset},
        )

        if response.status_code > 205:
            raise FetchingException(f"failed to fetch projects from GitHub: {response.text}")

        data = response.json()

        # {
        #     "oshwaUid": "SE000004",
        #     "responsibleParty": "arturo182",
        #     "country": "Sweden",
        #     "publicContact": "oledpmod@solder.party",
        #     "projectName": "0.95\" OLED PMOD",
        #     "projectWebsite": "https://github.com/arturo182/pmod_rgb_oled_0.95in/",
        #     "projectVersion": "1.0",
        #     "projectDescription": "A tiny color OLED!\r\n\r\nPerfect solution if you need a small display with vivid, high-contrast 16-bit color. PMOD connector can be used with FPGA and MCU dev boards\r\n\r\nThe display itself is a 0.95&quot; color OLED, the resolution is 96x64 RGB pixels.\r\n\r\nThe display is driven by the SSD1331 IC, you can control it with a 4-wire write-only SPI. The board only supports 3.3V logic.",
        #     "primaryType": "Other",
        #     "additionalType": [
        #         "Electronics"
        #     ],
        #     "projectKeywords": [
        #         "oled",
        #         "display",
        #         "pmod"
        #     ],
        #     "citations": [],
        #     "documentationUrl": "https://github.com/arturo182/pmod_rgb_oled_0.95in/",
        #     "hardwareLicense": "CERN",
        #     "softwareLicense": "No software",
        #     "documentationLicense": "CC BY-SA",
        #     "certificationDate": "2020-05-04T00:00-04:00"
        # },

        last_visited = datetime.now(timezone.utc)
        for item in data['items']:
            oshwa_logger.info(f"Convert item {item.get('projectName')}..")

            item['lastVisited'] = last_visited
            item["fetcher"] = self.NAME

            project = self._normalizer.normalize(item)
            oshwa_logger.debug("yield project %s", project.id)
            yield project

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
