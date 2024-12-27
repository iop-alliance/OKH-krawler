# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from krawl.cli.command import KrawlCommand
from krawl.cli.command.list.fetchers import ListFetchersCommand


class ListCommand(KrawlCommand):
    """Fetch a project from a platform.

    list
    """

    commands = [
        ListFetchersCommand(),
    ]

    def handle(self):
        self.call("help", "list")
