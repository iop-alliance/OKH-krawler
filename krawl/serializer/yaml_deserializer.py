from __future__ import annotations

from collections.abc import Mapping

import yaml

from krawl.errors import DeserializerError
from krawl.normalizer import Normalizer
from krawl.project import Project
from krawl.serializer import ProjectDeserializer


class YAMLProjectDeserializer(ProjectDeserializer):

    def deserialize(self, serialized: str | bytes, normalizer: Normalizer, enrich: dict = None) -> Project:
        try:
            deserialized = yaml.safe_load(serialized)
        except Exception as err:
            raise DeserializerError("failed to deserialize YAML: {err}") from err
        if not isinstance(deserialized, Mapping):
            raise DeserializerError("invalid format")
        if enrich:
            deserialized.update(enrich)
        return normalizer.normalize(deserialized)
