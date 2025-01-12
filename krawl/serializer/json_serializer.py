# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2023 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from krawl.fetcher.result import FetchResult
from krawl.model.project import Project
from krawl.serializer import Serializer
from krawl.serializer.util import json_serialize


class JsonSerializer(Serializer):

    @classmethod
    def extensions(cls) -> list[str]:
        return ["json"]

    def serialize(self, fetch_result: FetchResult, project: Project) -> str:
        return json_serialize(
            project)  # FIXME nonononono.. not so fast! missing data-set and fetch result and such stuff
