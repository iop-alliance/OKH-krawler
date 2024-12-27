# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from krawl.model.project import Project
from krawl.normalizer import Normalizer


class ProjectSerializer:
    """Interface for serializing project metadata."""

    @classmethod
    def extensions(cls) -> list[str]:
        """Returns a list of supported file extensions in all lower-case,
        without a leading dot."""
        raise NotImplementedError()

    def serialize(self, project: Project) -> str:
        raise NotImplementedError()


class ProjectDeserializer:
    """Interface for deserializing project metadata."""

    @classmethod
    def extensions(cls) -> list[str]:
        """Returns a list of supported file extensions in all lower-case."""
        raise NotImplementedError()

    def deserialize(self, serialized: str | bytes, normalizer: Normalizer, enrich: dict | None = None) -> Project:
        raise NotImplementedError()
