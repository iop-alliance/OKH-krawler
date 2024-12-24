from __future__ import annotations

from krawl.model.project import Project
from krawl.normalizer import Normalizer
from krawl.serializer.json_serializer import JsonProjectSerializer
from krawl.serializer.rdf_deserializer import RDFProjectDeserializer
from krawl.serializer.rdf_serializer import RDFProjectSerializer
from krawl.serializer.toml_deserializer import TOMLProjectDeserializer
from krawl.serializer.toml_serializer import TOMLProjectSerializer
from krawl.serializer.yaml_deserializer import YAMLProjectDeserializer


class SerializerFactory():

    def __init__(self, **kwargs) -> None:
        self._serializers = {}
        self._init_serializers(**kwargs)

    def serialize(self, suffix: str, project: Project) -> str:
        serializer = self._serializers.get(suffix.lower())
        if not serializer:
            raise ValueError(f"Unknown serializer type: '{suffix}'")
        return serializer.serialize(project)

    def _init_serializers(self):

        tmp_serializers = [
            JsonProjectSerializer(),
            TOMLProjectSerializer(),
            RDFProjectSerializer(),
        ]
        for serializer in tmp_serializers:
            for ext in serializer.extensions():
                self._serializers[ext] = serializer


class DeserializerFactory():

    def __init__(self, **kwargs) -> None:
        self._deserializers = {}
        self._init_deserializer(**kwargs)

    def deserialize(self, suffix: str, serialized: str | bytes, normalizer: Normalizer, enrich: dict = None) -> Project:
        deserializer = self._deserializers.get(suffix.lower())
        if not deserializer:
            raise ValueError(f"Unknown deserializer type: '{suffix}'")
        return deserializer.deserialize(serialized, normalizer, enrich)

    def _init_deserializer(self):

        tmp_deserializers = [
            YAMLProjectDeserializer(),
            TOMLProjectDeserializer(),
            RDFProjectDeserializer(),
        ]
        for deserializer in tmp_deserializers:
            for ext in deserializer.extensions():
                self._deserializers[ext] = deserializer
