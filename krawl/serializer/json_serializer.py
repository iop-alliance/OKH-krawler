# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2023 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from krawl.model.project import Project
from krawl.serializer import ProjectSerializer
from krawl.serializer.util import json_serialize


class JsonProjectSerializer(ProjectSerializer):

    @classmethod
    def extensions(cls) -> list[str]:
        return ["json"]

    def serialize(self, project: Project) -> str:
        return json_serialize(project)
