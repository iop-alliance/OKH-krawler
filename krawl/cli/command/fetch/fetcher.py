from __future__ import annotations

from pathlib import Path

from clikit.api.args.format import Option

from krawl.cli.command import KrawlCommand
from krawl.fetcher.factory import FetcherFactory
from krawl.log import get_child_logger
from krawl.reporter import Status
from krawl.reporter.dummy import DummyReporter
from krawl.reporter.file import FileReporter
from krawl.repository.factory import ProjectRepositoryFactory
from krawl.repository.fetcher_state import FetcherStateRepositoryFile
from krawl.validator.strict import StrictValidator

log = get_child_logger("fetch")


class FetcherXCommand(KrawlCommand):

    def __init__(self, name):
        super().__init__()
        self.name = name
        self._config.set_name(name)
        self._config.set_description(f"Find and fetch all projects from {name}.")
        self._config.add_option(
            long_name="repository",
            short_name="r",
            default=["file"],
            flags=Option.MULTI_VALUED,
            description="Repository to save the projects to"
            f" (available: {', '.join(ProjectRepositoryFactory.list_available_repositories())})",
        )
        self._config.add_option(
            long_name="start-over",
            flags=Option.NO_VALUE,
            description="Don't start at last saved state",
        )
        self._config.add_option(
            long_name="report",
            flags=Option.REQUIRED_VALUE,
            description="Path of reporting file",
        )
        # add options from config schema
        self._config_schema = self._load_config_schema(enabled_fetchers=[name])
        self._add_options_from_schema(schema=self._config_schema)

    def handle(self):
        start_over = self.option("start-over")
        enabled_repositories = self.option("repository")
        report_path = Path(self.option("report")) if self.option("report") else None

        # load, normalize and validate config
        config = self._load_config(enabled_repositories=enabled_repositories, enabled_fetchers=[self.name])

        # initialize fetchers and repositories
        if config.database.type == "file":
            fetcher_state_repository = FetcherStateRepositoryFile(config.database.path)
        else:
            raise ValueError(f"Unknown database type: {config.database.type}")
        fetcher_factory = FetcherFactory(fetcher_state_repository, config.fetchers, [self.name])
        repository_factory = ProjectRepositoryFactory(config.repositories, enabled_repositories)
        fetcher = fetcher_factory.get(self.name)
        validator = StrictValidator()

        # create a reporter
        if report_path:
            reporter = FileReporter(report_path)
        else:
            reporter = DummyReporter()

        # perform the deed
        log.info("fetching all projects from %s", self.name)
        for project in fetcher.fetch_all(start_over=start_over):
            ok, reason = validator.validate(project)
            if ok:
                reporter.add(project.id, Status.OK)
            else:
                reporter.add(project.id, Status.FAILED, reason)
                log.info("Skipping project '%s' because: %s", project.id, reason[0])
                continue
            repository_factory.store(project)
            log.info("Saved project '%s'", project.id)

        reporter.close()
