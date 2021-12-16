import logging
from urllib.parse import urlparse

import krawl.config as config
from krawl.cli.command import KrawlCommand
from krawl.fetcher.factory import FetcherFactory, is_fetcher_available
from krawl.serializer.rdf import RDFProjectSerializer
from krawl.serializer.yaml import YAMLProjectSerializer
from krawl.storage.fetcher_state_storage_file import FetcherStateStorageFile
from krawl.storage.project_storage_file import ProjectStorageFile
from krawl.validator.dummy import DummyValidator
from krawl.validator.strict import StrictValidator

log = logging.getLogger("url-fetch-command")


class FetchURLCommand(KrawlCommand):
    """Fetch projects from given URLs.

    url
        {url* : URLs to fetch from}
        {--n|no-validate : Don't validate project before saving it}
    """

    def handle(self):
        urls = self.argument("url")
        no_validate = self.option("no-validate")

        fetcher_state_storage = FetcherStateStorageFile(config.WORKDIR)
        fetcher_factory = FetcherFactory(fetcher_state_storage)

        # parse urls
        ids = []
        for url in urls:
            parsed_url = urlparse(url)
            platform = parsed_url.hostname
            splitted_path = parsed_url.path.split("/")
            if len(splitted_path) < 3:
                self.line_error(f"invalid URL '{url}'")
                return 1
            owner, name = splitted_path[1:3]
            id = f"{platform}/{owner}/{name}"
            ids.append(id)
            if not is_fetcher_available(id):
                self.line_error(f"no fetcher available for '{platform}'")
                return 1

        # fetch to projects
        if no_validate:
            validator = DummyValidator()
        else:
            validator = StrictValidator()
        yaml_serializer = YAMLProjectSerializer()
        yaml_storage = ProjectStorageFile(base_path=config.WORKDIR, extension="yml", serializer=yaml_serializer)
        rdf_serializer = RDFProjectSerializer()
        rdf_storage = ProjectStorageFile(base_path=config.WORKDIR, extension="ttl", serializer=rdf_serializer)
        for id in ids:
            project = fetcher_factory.fetch(id)
            ok, reason = validator.validate(project)
            if not ok:
                log.info("Skipping project '%s' because: %s", project.id, reason[0])
                continue
            yaml_storage.store(project)
            rdf_storage.store(project)
