import logging

import krawl.config as config
from krawl.cli.command import KrawlCommand
from krawl.fetcher.factory import FetcherFactory
from krawl.fetcher.wikifactory import WikifactoryFetcher
from krawl.serializer.json import JSONProjectSerializer
from krawl.serializer.rdf import RDFProjectSerializer
from krawl.serializer.toml import TOMLProjectSerializer
from krawl.serializer.yaml import YAMLProjectSerializer
from krawl.storage.fetcher_state_storage_file import FetcherStateStorageFile
from krawl.storage.project_storage_file import ProjectStorageFile
from krawl.validator.dummy import DummyValidator
from krawl.validator.strict import StrictValidator

log = logging.getLogger("wikifactory-fetch-command")


class FetcherXCommand(KrawlCommand):
    """Fetch all projects from {}.

    xxx
        {--s|start-over : Don't start at last saved state}
        {--n|no-validate : Don't validate project before saving it}
        {--b|batch-size= : Number of requests to perform at a time}
        {--t|timeout= : Max seconds to wait for a not responding service}
    """

    def __init__(self, name):
        super().__init__()
        self.name = name
        self._config.set_name(name)
        self._config.set_description(self._config._description.format(name))

    def handle(self):
        start_over = self.option("start-over")
        no_validate = self.option("no-validate")
        batch_size = self.option_int("batch-size", default=25, min=1)
        timeout = self.option_int("batch-size", default=10, min=0)

        fetcher_state_storage = FetcherStateStorageFile(config.WORKDIR)
        fetcher_factory = FetcherFactory(state_storage=fetcher_state_storage, batch_size=batch_size, timeout=timeout)
        self._fetcher = fetcher_factory.get_fetcher(self.name)

        if no_validate:
            validator = DummyValidator()
        else:
            validator = StrictValidator()
        yaml_serializer = YAMLProjectSerializer()
        yaml_storage = ProjectStorageFile(base_path=config.WORKDIR, extension="yml", serializer=yaml_serializer)
        rdf_serializer = RDFProjectSerializer()
        rdf_storage = ProjectStorageFile(base_path=config.WORKDIR, extension="ttl", serializer=rdf_serializer)
        log.info("fetching all projects from %s", self.name)
        for project in self._fetcher.fetch_all(start_over=start_over):
            ok, reason = validator.validate(project)
            if not ok:
                log.info("Skipping project '%s' because: %s", project.id, reason[0])
                continue
            yaml_storage.store(project)
            rdf_storage.store(project)
