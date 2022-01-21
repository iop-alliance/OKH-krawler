from __future__ import annotations

from krawl.normalizer import Normalizer
from krawl.project import Project
from krawl.serializer.json_deserializer import JSONProjectDeserializer
from krawl.serializer.json_serializer import JSONProjectSerializer
from krawl.serializer.rdf_deserializer import RDFProjectDeserializer
from krawl.serializer.rdf_serializer import RDFProjectSerializer
from krawl.serializer.toml_deserializer import TOMLProjectDeserializer
from krawl.serializer.toml_serializer import TOMLProjectSerializer
from krawl.serializer.yaml_deserializer import YAMLProjectDeserializer
from krawl.serializer.yaml_serializer import YAMLProjectSerializer


class SerializerFactory():

    def __init__(self, **kwargs) -> None:
        self._serializers = {}
        self._init_serializers(**kwargs)

    def serialize(self, suffix: str, project: Project) -> str:
        serializer = self._serializers.get(suffix.lower())
        if not serializer:
            raise Exception(f"Unknown type '{suffix}'")
        return serializer.serialize(project)

    def _init_serializers(self):
        yaml_serializer = YAMLProjectSerializer()
        self._serializers[".yml"] = yaml_serializer
        self._serializers[".yaml"] = yaml_serializer

        toml_serializer = TOMLProjectSerializer()
        self._serializers[".toml"] = toml_serializer

        json_serializer = JSONProjectSerializer()
        self._serializers[".json"] = json_serializer

        rdf_serializer = RDFProjectSerializer()
        self._serializers[".ttl"] = rdf_serializer


class DeserializerFactory():

    def __init__(self, **kwargs) -> None:
        self._deserializer = {}
        self._init_deserializer(**kwargs)

    def deserialize(self, suffix: str, serialized: str | bytes, normalizer: Normalizer, enrich: dict = None) -> Project:
        deserializer = self._deserializer.get(suffix.lower())
        if not deserializer:
            raise Exception(f"Unknown type '{suffix}'")
        return deserializer.deserialize(serialized, normalizer, enrich)

    def _init_deserializer(self):
        yaml_deserializer = YAMLProjectDeserializer()
        self._deserializer[".yml"] = yaml_deserializer
        self._deserializer[".yaml"] = yaml_deserializer

        toml_deserializer = TOMLProjectDeserializer()
        self._deserializer[".toml"] = toml_deserializer

        json_deserializer = JSONProjectDeserializer()
        self._deserializer[".json"] = json_deserializer

        rdf_deserializer = RDFProjectDeserializer()
        self._deserializer[".ttl"] = rdf_deserializer
