# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json

import toml

from krawl.errors import SerializerError
from krawl.model.project import Project
from krawl.serializer import ProjectSerializer
from krawl.serializer.json_serializer import JsonProjectSerializer


class TOMLProjectSerializer(ProjectSerializer):

    @classmethod
    def extensions(cls) -> list[str]:
        return ["toml"]

    def __init__(self) -> None:
        self.json_serializer = JsonProjectSerializer()

    def serialize(self, project: Project) -> str:
        try:
            # serialized = toml.dumps(project.as_dict())
            project_json = self.json_serializer.serialize(project)
            serialized = toml.dumps(json.loads(project_json))
        except Exception as err:
            raise SerializerError(f"failed to serialize TOML: {err}") from err
        return serialized
