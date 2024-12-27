# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
import os
from pathlib import Path

from krawl.config import Config
from krawl.fetcher.result import FetchResult
# from krawl.fetcher.event import FailedFetch # TODO Maybe write a marker file on a failed fetch?
from krawl.log import get_child_logger
from krawl.model.hosting_unit import HostingUnitId
from krawl.model.manifest import ManifestFormat
from krawl.repository.fetch_result_repository import FetchResultRepository
from krawl.serializer.util import json_serialize

log = get_child_logger("repo_file")


class FetchResultRepositoryWorkdir(FetchResultRepository):
    """Stores fetch results in the local file-system."""

    CONFIG_SCHEMA: dict = {
        "type": "dict",
        "default": {},
        "meta": {
            "long_name": "file",
        },
        "schema": {
            "workdir": {
                "type": "path",
                "required": True,
                "nullable": False,
                "default": Path("./workdir"),
                "meta": {
                    "long_name": "workdir",
                    "description": "Base path to store and load projects in the filesystem"
                }
            },
        },
    }

    def __init__(self, repository_config: Config):
        self._workdir = repository_config.workdir

    def _store_file(self, dir: Path, file_stem: str, file_type: ManifestFormat, content: str | bytes | dict) -> None:
        file_path: Path = Path(os.path.join(dir, f"{file_stem}.{file_type}"))
        if isinstance(content, dict):
            content = json.dumps(content, indent=2)
        if isinstance(content, str):
            file_path.write_text(content)
        elif isinstance(content, bytes):
            file_path.write_bytes(content)
        else:
            raise TypeError(
                f"Fetch result data content must be of type `str`, `bytes` or `dict`, but is: {type(content)}")

    def store(self, fetch_result: FetchResult) -> None:
        hosting_unit_id: HostingUnitId = fetch_result.data_set.hosting_unit_id
        project_dir: Path = Path(os.path.join(self._workdir, hosting_unit_id.to_path()))
        log.debug(f"Saving '{hosting_unit_id}' to '{str(project_dir)}' ...")
        project_dir.mkdir(parents=True, exist_ok=True)

        data_set_json: str = json_serialize(fetch_result.data_set)
        self._store_file(project_dir, "meta", ManifestFormat.JSON, data_set_json)

        self._store_file(project_dir, "orig", fetch_result.data.format, fetch_result.data.content)

        log.debug(f"Saving '{hosting_unit_id}' to '{str(project_dir)}' - done.")
