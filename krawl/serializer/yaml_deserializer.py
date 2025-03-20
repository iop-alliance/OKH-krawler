# SPDX-FileCopyrightText: 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from collections.abc import Mapping

import yaml

from krawl.errors import DeserializerError
from krawl.fetcher.result import FetchResult
from krawl.model.project import Project
from krawl.normalizer import Normalizer
from krawl.recursive_type import RecDict
from krawl.serializer import Deserializer


class YAMLDeserializer(Deserializer):

    @classmethod
    def extensions(cls) -> list[str]:
        return ["yml", "yaml"]

    def deserialize(self,
                    serialized: str | bytes,
                    normalizer: Normalizer,
                    enrich: dict | None = None) -> tuple[FetchResult, Project]:
        try:
            deserialized: RecDict = yaml.safe_load(serialized)
        except Exception as err:
            raise DeserializerError(f"failed to deserialize YAML: {err}") from err
        if not isinstance(deserialized, Mapping):
            raise DeserializerError("invalid format")
        if enrich:
            deserialized.update(enrich)
        return (None, normalizer.normalize(deserialized))
