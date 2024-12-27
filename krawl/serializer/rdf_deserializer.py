# SPDX-FileCopyrightText: 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from krawl.model.project import Project
from krawl.normalizer import Normalizer
from krawl.serializer import ProjectDeserializer


class RDFProjectDeserializer(ProjectDeserializer):

    @classmethod
    def extensions(cls) -> list[str]:
        return ["ttl"]

    def deserialize(self, serialized: str | bytes, normalizer: Normalizer, enrich: dict | None = None) -> Project:
        raise NotImplementedError()
