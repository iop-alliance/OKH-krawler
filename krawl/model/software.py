# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass

from krawl.model.file import File


@dataclass(slots=True)
class Software:
    """Software data model."""

    installation_guide: File
    documentation_language: str | None = None
    license: str | None = None
    licensor: str | None = None
    release: str | None = None
