# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2022 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
import os
from urllib.parse import unquote

from krawl.config import Config
from krawl.errors import FetcherError, NotFound, ParserError
from krawl.fetcher import Fetcher
from krawl.fetcher.event import FailedFetch
from krawl.fetcher.result import FetchResult
from krawl.fetcher.util import is_accepted_manifest_file_name, is_empty
from krawl.log import get_child_logger
from krawl.model.data_set import CrawlingMeta, DataSet
from krawl.model.hosting_id import HostingId
from krawl.model.hosting_unit import HostingUnitIdForge
from krawl.model.manifest import Manifest, ManifestFormat
from krawl.model.project_id import ProjectId
from krawl.model.project_part_reference import Ref
from krawl.model.sourcing_procedure import SourcingProcedure
from krawl.repository import FetcherStateRepository

__long_name__: str = "manifests-repo"
__hosting_id__: HostingId = HostingId.MANIFESTS_REPO # TODO FIXME HACK
__sourcing_procedure__: SourcingProcedure = SourcingProcedure.MANIFEST
log = get_child_logger(__long_name__)

MANIFEST_FILE_EXTENSIONS = ['toml', 'yaml', 'yml', 'json', 'ttl', 'rdf', 'jsonld']
MANIFEST_FILES_GLOB = ("**/?(*.)okh.{", ",".join(MANIFEST_FILE_EXTENSIONS), "}")
TOML_MANIFEST_FILES_GLOB_1 = "**/okh.toml"
TOML_MANIFEST_FILES_GLOB_2 = "**/*.okh.toml"

class ManifestsRepoFetcher(Fetcher):
    """Fetcher for a local directory.

    Said directory might be a git repo "scraped" by the rust okh-scraper.
    So really, this just parses a bunch of local '?(*.)okh.toml' files
    within a directory tree."""
    CONFIG_SCHEMA_EXTRA: dict = {
        "scrape-dir": {
            "type": "string",
            "coerce": "strip_str",
            "required": True,
            "nullable": False,
            "meta": {
                "long_name": "scrape-dir",
                "description": "Local file-system path to a directory(-tree) containing '?(*.)okh.toml' manifest files"
            }
        },
    }
    CONFIG_SCHEMA = Fetcher._generate_config_schema(long_name=__long_name__, extra_schema=CONFIG_SCHEMA_EXTRA)

    def __init__(self, state_repository: FetcherStateRepository, config: Config) -> None:
        super().__init__(state_repository=state_repository)
        self.scrape_dir: Path = Path(str(config.get("scrape-dir")))
        self.repo_url = unquote(self.scrape_dir.name)
        # print(self.repo_url)
        # exit(99)

    def __fetch_one(self, hosting_unit_id: HostingUnitIdForge, manifest_url: str, okh_manifest_path: Path) -> FetchResult:
        try:
            log.debug("fetching project '%s' ...", str(okh_manifest_path))

            # check file name
            if not is_accepted_manifest_file_name(okh_manifest_path):
                raise FetcherError(f"Not an accepted manifest file name: '{okh_manifest_path.name}'")

            last_visited = datetime.fromtimestamp(os.path.getmtime(okh_manifest_path))
            manifest_contents = okh_manifest_path.read_text()

            # check file contents
            if is_empty(manifest_contents):
                raise FetcherError(f"Manifest file is empty: '{okh_manifest_path}'")
            # if is_binary(manifest_contents):
            #     raise FetcherError(f"Manifest file is binary (should be text): '{manifest_dl_url}'")

            format_suffix = okh_manifest_path.suffix.lower().lstrip('.')
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
                okhv_fetched="OKH-LOSHv1.0",  # FIXME Not good, not right
                crawling_meta=CrawlingMeta(
                    sourcing_procedure=__sourcing_procedure__,
                    last_visited=last_visited,
                    first_visited=last_visited,
                    last_successfully_visited=last_visited,
                    last_detected_change=None,
                    created_at=None,
                    visits=1,
                    changes=0,
                    manifest=manifest_url,
                ),
                hosting_unit_id=hosting_unit_id,
                license=Ref.DOCUMENTATION,
                creator=Ref.DOCUMENTATION,
                organization=Ref.DOCUMENTATION,
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

    def _extract_url_from_file(self, manifest_file: Path) -> tuple[str, HostingUnitIdForge, Path | None]:
        url = f"{self.repo_url}/{str(manifest_file)}"
        try:
            hosting_unit_id, path_raw = HostingUnitIdForge.from_url(url)
        except ParserError as err:
            raise FetcherError(f"Invalid git forge manifest file URL: '{url}'") from err
        return url, hosting_unit_id, path_raw

    def fetch(self, project_id: ProjectId) -> FetchResult:
        hosting_unit_id, path_raw = self._parse_project_url(project_id.uri)

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
        num_fetched_projects = 0
        for glob in [TOML_MANIFEST_FILES_GLOB_1, TOML_MANIFEST_FILES_GLOB_2]:
            log.debug("fetching projects with recursive glob '%s' ...", glob)
            for potential_toml_manifest_path in self.scrape_dir.rglob(glob):
                # print(potential_toml_manifest_path.name)
                num_fetched_projects = num_fetched_projects + 1

                try:
                    manifest_url, hosting_unit_id, _path = self._extract_url_from_file(potential_toml_manifest_path)
                except FetcherError as err:
                    log.warning(f"Skipping project file, because: {err}")
                    continue

                # file_name = Path(potential_toml_manifest_path.name)
                # if not is_accepted_manifest_file_name(file_name):
                #     log.warning(f"Not an accepted manifest file name (in this URL): '{manifest_url}'")
                #     continue

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
                    yield self.__fetch_one(hosting_unit_id, manifest_url, potential_toml_manifest_path)
                except FetcherError as err:
                    log.debug(f"skipping file, because: {err}")

        self._state_repository.delete(__hosting_id__)
        log.debug("fetched %d projects from local dir '%s'", num_fetched_projects, self.scrape_dir)
