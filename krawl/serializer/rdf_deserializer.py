from __future__ import annotations

from krawl.normalizer import Normalizer
from krawl.project import Project
from krawl.serializer import ProjectDeserializer


class RDFProjectDeserializer(ProjectDeserializer):

    def deserialize(self, serialized: str | bytes, normalizer: Normalizer, enrich: dict = None) -> Project:
        raise NotImplementedError()
