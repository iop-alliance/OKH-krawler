# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json

import toml

from krawl.errors import SerializerError
from krawl.fetcher.result import FetchResult
from krawl.model.project import Project
from krawl.serializer import Serializer
from krawl.serializer.json_serializer import JsonSerializer


class TOMLSerializer(Serializer):

    @classmethod
    def extensions(cls) -> list[str]:
        return ["toml"]

    def __init__(self) -> None:
        self.json_serializer = JsonSerializer()

    def serialize(self, fetch_result: FetchResult, project: Project) -> str:
        try:
            # serialized = toml.dumps(project.as_dict())
            project_json = self.json_serializer.serialize(fetch_result, project)
            serialized = toml.dumps(json.loads(project_json))
        except Exception as err:
            raise SerializerError(f"failed to serialize TOML: {err}") from err
        return serialized
