# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from krawl.cli.command import KrawlCommand
from krawl.cli.command.fetch.fetcher import FetcherXCommand
from krawl.cli.command.fetch.url import FetchURLCommand
from krawl.fetcher.factory import FetcherFactory


def _dynamic_fetcher_commands() -> list[KrawlCommand]:
    return [FetcherXCommand(fetcher) for fetcher in FetcherFactory.list_available_fetchers()]


class FetchCommand(KrawlCommand):
    """Fetches a single or many project from a hosting system (e.g. GitHub or IPFS).

    fetch
    """

    commands = [
        FetchURLCommand(),
    ] + _dynamic_fetcher_commands()

    def handle(self):
        self.call("help", "fetch")
