from __future__ import annotations

import json
from collections.abc import Mapping

from krawl.errors import DeserializerError
from krawl.normalizer import Normalizer
from krawl.project import Project
from krawl.serializer import ProjectDeserializer


class JSONProjectDeserializer(ProjectDeserializer):

    def deserialize(self, serialized: str | bytes, normalizer: Normalizer, enrich: dict = None) -> Project:
        deserialized = json.loads(serialized)
        if not isinstance(deserialized, Mapping):
            raise DeserializerError("invalid format")
        if enrich:
            deserialized.update(enrich)
        return normalizer.normalize(deserialized)
