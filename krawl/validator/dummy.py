# SPDX-FileCopyrightText: 2021 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from krawl.model.project import Project
from krawl.validator import Validator


class DummyValidator(Validator):

    def validate(self, project: Project) -> tuple[bool, list[str] | None]:
        return True, None
