from __future__ import annotations

from collections.abc import Mapping

import toml

from krawl.errors import DeserializerError
from krawl.normalizer import Normalizer
from krawl.project import Project
from krawl.serializer import ProjectDeserializer


class TOMLProjectDeserializer(ProjectDeserializer):

    def deserialize(self, serialized: str | bytes, normalizer: Normalizer, enrich: dict = None) -> Project:
        try:
            if isinstance(serialized, bytes):
                serialized = serialized.decode(encoding="UTF-8", errors="ignore")
            deserialized = toml.loads(serialized)
        except Exception as err:
            raise DeserializerError(f"failed to deserialize TOML: {err}") from err

        if not isinstance(deserialized, Mapping):
            raise DeserializerError("invalid format")
        if enrich:
            deserialized.update(enrich)
        return normalizer.normalize(deserialized)
