from __future__ import annotations

from pathlib import Path
import sys

from clikit.api.args.format import Option

from krawl.cli.command import KrawlCommand
from krawl.fetcher.factory import FetcherFactory
from krawl.log import get_child_logger
from krawl.project import ProjectID
from krawl.repository.factory import ProjectRepositoryFactory
from krawl.repository.fetcher_state import FetcherStateRepositoryFile
from krawl.validator.strict import StrictValidator

log = get_child_logger("fetch")


class FetchURLCommand(KrawlCommand):
    """Fetch projects from given URLs.

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
            description=
            f"Repository to save the projects to (available: {', '.join(ProjectRepositoryFactory.list_available_repositories())})",
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
        urls = self.argument("url")
        enabled_repositories = self.option("repository")
        report_path = Path(self.option("report")) if self.option("report") else None

        # parse urls
        ids = []
        required_fetchers = set()
        for url in urls:
            id = ProjectID.from_url(url)
            required_fetchers.add(id.platform)
            ids.append(id)

        # load, normalize and validate config
        config = self._load_config(enabled_repositories=enabled_repositories, enabled_fetchers=required_fetchers)

        # initialize fetchers and repositories
        if config.database.type == "file":
            fetcher_state_repository = FetcherStateRepositoryFile(config.database.path)
        fetcher_factory = FetcherFactory(fetcher_state_repository, config.fetchers, list(required_fetchers))
        repository_factory = ProjectRepositoryFactory(config.repositories, enabled_repositories)
        validator = StrictValidator()

        # perform the deed
        report = []
        failures = 0
        for id in ids:
            project = fetcher_factory.fetch(id)
            ok, reason = validator.validate(project)
            if not ok:
                log.info("Skipping project '%s' because: %s", project.id, reason[0])
                report.append(f"Skipped '{project.id}': {', '.join(reason)}")
                failures = min(failures + 1, 255)
                continue
            repository_factory.store(project)
            report.append(f"Added '{project.id}'")

        if report_path:
            with report_path.open("w") as f:
                f.writelines(report)
        else:
            sys.stdout.writelines(report)

        if failures > 0:
            sys.exit(failures)
