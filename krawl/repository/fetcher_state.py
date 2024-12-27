# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
from pathlib import Path

from krawl.log import get_child_logger
from krawl.model.hosting_id import HostingId
from krawl.repository import FetcherStateRepository

log = get_child_logger("fetcher_state")


class FetcherStateRepositoryFile(FetcherStateRepository):
    """Storing and loading the state of a fetcher."""

    def __init__(self, base_path: Path):
        self._base_path = base_path / "__fetcher__"
        # print(f"self._base_path: {self._base_path}")
        # raise SystemError(45)

    def load(self, fetcher: HostingId) -> dict:
        path = self._get_path(fetcher)
        if not path.exists():
            log.debug("state repository for fetcher '%s' doesn't exist, returning empty default", fetcher)
            return {}
        serialized = path.read_text()
        deserialized = json.loads(serialized)
        return deserialized

    def store(self, fetcher: HostingId, state: dict) -> None:
        path = self._get_path(fetcher)
        log.debug("saving state of fetcher '%s' (%s)", fetcher, str(path))
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(state, indent=4)
        path.write_text(serialized)

    def delete(self, fetcher: HostingId) -> bool:
        path = self._get_path(fetcher)
        if not path.exists():
            return False
        log.debug("deleting state repository of fetcher '%s' (%s)", fetcher, str(path))
        path.unlink()
        return True

    def _get_path(self, fetcher: HostingId) -> Path:
        return self._base_path / (fetcher + ".json")
