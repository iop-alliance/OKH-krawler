# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2022 Nicolas Traeder <nicolas@konek.to>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from collections.abc import Generator

from krawl.config import Config
from krawl.errors import FetcherError, NormalizerError
from krawl.fetcher import Fetcher, appropedia, github, manifests_repo, oshwa, thingiverse
from krawl.fetcher.event import FetchListener
# from krawl.cli.command.fetch import NormalizationListener
from krawl.fetcher.result import FetchResult
from krawl.log import get_child_logger
from krawl.model.hosting_id import HostingId
from krawl.model.project_id import ProjectId
from krawl.normalizer import Normalizer
from krawl.normalizer.factory import NormalizerFactory
from krawl.repository import FetcherStateRepository
from krawl.repository.fetch_result_repository import FetchResultRepository
from krawl.repository.fetch_result_repository_workdir import FetchResultRepositoryWorkdir
from krawl.serializer.factory import Serializer
from krawl.serializer.rdf_serializer import RDFSerializer
from krawl.serializer.toml_serializer import TOMLSerializer

log = get_child_logger("fetcher-factory")

_fetcher_classes = {
    appropedia.__hosting_id__: appropedia.AppropediaFetcher,
    github.__hosting_id__: github.GitHubFetcher,
    oshwa.__hosting_id__: oshwa.OshwaFetcher,
    thingiverse.__hosting_id__: thingiverse.ThingiverseFetcher,
    manifests_repo.__hosting_id__: manifests_repo.ManifestsRepoFetcher,
}


class NormalizationListener(FetchListener):

    def __init__(self, fetch_result_repository: FetchResultRepository) -> None:
        self.normalizer_factory = NormalizerFactory()
        self.serializer_toml: Serializer = TOMLSerializer()
        self.serializer_rdf: Serializer = RDFSerializer()
        self.fetch_result_repository: FetchResultRepository = fetch_result_repository

    def fetched(self, fetch_result: FetchResult) -> None:
        normalizer: Normalizer = self.normalizer_factory.get(fetch_result.data_set.hosting_unit_id.hosting_id())
        try:
            project = normalizer.normalize(fetch_result)
        except NormalizerError as err:
            log.warn("Failed to normalize fetch result '%s': %s", fetch_result.data_set.hosting_unit_id, err)
            return
        toml: str = self.serializer_toml.serialize(fetch_result, project)
        project.normalized_toml = toml
        (toml_ttl, meta_ttl, ttl) = self.serializer_rdf.serialize(fetch_result, project)
        self.fetch_result_repository.store_final(fetch_result, toml_ttl, meta_ttl, ttl)


class FetcherFactory:

    def __init__(self,
                 repository_config: Config,
                 state_repository: FetcherStateRepository,
                 fetchers_config: Config,
                 enabled: list[HostingId] | None = None) -> None:
        self._fetchers: dict = {}
        self._enabled = enabled or list(_fetcher_classes.keys())

        for e in self._enabled:
            assert e in _fetcher_classes

        self._init_fetchers(repository_config, state_repository, fetchers_config, self._enabled)

    @property
    def enabled(self) -> list[HostingId]:
        return self._enabled

    @classmethod
    def get_config_schemas(cls, hosting_ids: list[HostingId] | None = None) -> dict[HostingId, dict]:
        if not hosting_ids:
            return {n: c.CONFIG_SCHEMA for n, c in _fetcher_classes.items()}
        schema = {}
        for hosting_id in hosting_ids:
            if hosting_id not in _fetcher_classes:
                raise FetcherError(
                    f"no fetcher available for '{hosting_id}', available are: {', '.join(_fetcher_classes.keys())}")
            schema[hosting_id] = _fetcher_classes[hosting_id].CONFIG_SCHEMA
        return schema

    def get_enabled_config_schemas(self) -> dict:
        return {e: _fetcher_classes[e].CONFIG_SCHEMA for e in self._enabled}

    @classmethod
    def list_available_fetchers(cls) -> list[HostingId]:
        return list(_fetcher_classes)

    @classmethod
    def is_fetcher_available(cls, hosting_id: HostingId) -> bool:
        return hosting_id in _fetcher_classes

    def get(self, hosting_id: HostingId) -> Fetcher:
        if hosting_id not in _fetcher_classes:
            raise FetcherError(
                f"no fetcher available for '{hosting_id}', available are: {', '.join(_fetcher_classes.keys())}")
        if hosting_id not in self._fetchers:
            raise FetcherError(f"fetcher '{hosting_id}' is not enabled")
        return self._fetchers[hosting_id]

    def get_all(self) -> Generator[Fetcher]:
        yield from self._fetchers.values()

    def fetch(self, project_id: ProjectId) -> FetchResult:
        """Call `fetch` function on fitting fetcher."""
        # TODO PRIORITY:LOW Also parsed within the individual fetcher. Maybe try to parse only once
        hosting_id = HostingId.from_url(project_id.uri)
        if hosting_id not in self._fetchers:
            raise FetcherError(
                f"No fetcher available for '{hosting_id}', available are: {', '.join(_fetcher_classes.keys())}")
        return self._fetchers[hosting_id].fetch(project_id)

    def fetch_all(self, start_over=True) -> Generator[FetchResult]:
        """Call `fetch_all` function on all enabled fetchers."""
        # TODO: should be parallelized
        for fetcher in self._fetchers.values():
            yield from fetcher.fetch_all(start_over=start_over)

    def add_fetch_listener(self, listener: FetchListener) -> None:
        for fetcher in self._fetchers.values():
            fetcher.add_fetch_listener(listener)

    def _init_fetchers(self, repository_config: Config, state_repository, fetchers_config: Config,
                       enabled: list[HostingId]):
        fetch_result_repository: FetchResultRepository = FetchResultRepositoryWorkdir(repository_config.file)
        for hosting_id, fetcher_class in _fetcher_classes.items():
            if hosting_id in enabled:
                fetcher = fetcher_class(state_repository, fetchers_config[hosting_id])
                fetcher.add_fetch_listener(fetch_result_repository)
                self._fetchers[hosting_id] = fetcher

        self.add_fetch_listener(NormalizationListener(fetch_result_repository))
