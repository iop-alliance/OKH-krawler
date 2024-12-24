from __future__ import annotations

from pathlib import Path

from clikit.api.args.format import Option

from krawl.cli.command import KrawlCommand
from krawl.fetcher.factory import FetcherFactory
from krawl.log import get_child_logger
from krawl.model.hosting_unit import HostingUnitId, HostingUnitIdFactory
from krawl.model.project_id import ProjectID
from krawl.reporter import Status
from krawl.reporter.dummy import DummyReporter
from krawl.reporter.file import FileReporter
from krawl.repository.factory import ProjectRepositoryFactory
from krawl.repository.fetcher_state import FetcherStateRepositoryFile
from krawl.validator.strict import StrictValidator

log = get_child_logger("fetch")


class FetchURLCommand(KrawlCommand):
    """Fetches projects from given URLs.

    url
        {url* : URLs to fetch from}
    """

    def __init__(self):
        super().__init__()
        self._config.add_option(
            long_name="repository",
            short_name="r",
            default=["file"],
            flags=Option.MULTI_VALUED,
            description="Repository to save the projects to"
            f" (available: {', '.join(ProjectRepositoryFactory.list_available_repositories())})",
        )
        self._config.add_option(
            long_name="report",
            flags=Option.REQUIRED_VALUE,
            description="Path of reporting file",
        )
        # add options from config schema
        self._config_schema = self._load_config_schema()
        self._add_options_from_schema(schema=self._config_schema)

    def handle(self):
        enabled_repositories = self.option("repository")
        report_path = Path(self.option("report")) if self.option("report") else None

        # parse urls
        ids = []
        required_fetchers_set = set()
        for url in self.argument("url"):
            hosting_unit_id, path = HostingUnitIdFactory.from_url(url)
            log.debug(f"Parsed hosting_unit_id: {hosting_unit_id}")
            required_fetchers_set.add(hosting_unit_id.hosting_id())
            project_id = ProjectID(uri=url)
            ids.append((project_id, hosting_unit_id, path))
        required_fetchers = list(required_fetchers_set)

        # load, normalize and validate config
        config = self._load_config(enabled_repositories=enabled_repositories, enabled_fetchers=required_fetchers)

        # initialize fetchers and repositories
        if config.database.type == "file":
            fetcher_state_repository = FetcherStateRepositoryFile(config.database.path)
        else:
            raise ValueError(f"Unknown database type: {config.database.type}")
        fetcher_factory = FetcherFactory(fetcher_state_repository, config.fetchers, required_fetchers)
        repository_factory = ProjectRepositoryFactory(config.repositories, enabled_repositories)
        validator = StrictValidator()

        # create a reporter
        if report_path:
            reporter = FileReporter(report_path)
        else:
            reporter = DummyReporter()

        # perform the deed
        failures = 0
        for project_id, _hosting_unit_id, _path in ids:
            project = fetcher_factory.fetch(project_id)
            ok, reason = validator.validate(project)
            if ok:
                reporter.add(project.id, Status.OK)
            else:
                reporter.add(project.id, Status.FAILED, reason)
                log.info("Skipping project '%s' because: %s", project.id, reason[0])
                failures = failures + 1
                continue
            log.debug("Project: %s", project)
            repository_factory.store(project)
            log.info("Saved project '%s'", project.id)

        reporter.close()

        if failures > 0:
            raise SystemExit(min(failures, 255))
