# SPDX-FileCopyrightText: 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2022 Nicolas Traeder <nicolas@konek.to>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import io
from pathlib import Path

from krawl.model.hosting_unit import HostingUnitId
from krawl.model.project import Project
from krawl.reporter import Reporter, Status


class FileReporter(Reporter):
    """Reporter on fetching results, that writes to a given file."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._file: io.TextIOWrapper
        self._open(path)

    def add(self,
            hosting_unit_id: HostingUnitId,
            status: Status,
            reasons: list[str] | None = None,
            project: Project | None = None) -> None:
        match status:
            case Status.OK | Status.UNKNOWN:
                line = f"{str(status):<8}: {str(hosting_unit_id)}\n"
            case Status.FAILED:
                line = f"{str(status):<8}: {str(hosting_unit_id)} : {', '.join(reasons if reasons else [])}\n"
            case _:
                raise ValueError(f"unknown status: {status}")
        self._file.write(line)

    def close(self) -> None:
        if self._file:
            self._file.close()

    def _open(self, path: Path):
        if path.exists() and not path.is_file():
            raise OSError(f"'{path}' is not a file")
        self._file = path.open("w")
