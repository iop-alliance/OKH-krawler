# SPDX-FileCopyrightText: 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2023 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from krawl.model.project import Project
from krawl.normalizer import Normalizer

from . import Deserializer, Serializer
from .json_serializer import JsonSerializer
from .rdf_deserializer import RDFDeserializer
from .rdf_serializer import RDFSerializer
from .toml_deserializer import TOMLDeserializer
from .toml_serializer import TOMLSerializer
from .yaml_deserializer import YAMLDeserializer


class SerializerFactory():

    def __init__(self, **kwargs) -> None:
        self._serializers: dict[str, Serializer] = {}
        self._init_serializers(**kwargs)

    def serialize(self, suffix: str, project: Project) -> str:
        serializer = self._serializers.get(suffix.lower())
        if not serializer:
            raise ValueError(f"Unknown serializer type: '{suffix}'")
        return serializer.serialize(project)

    def _init_serializers(self):

        tmp_serializers = [
            JsonSerializer(),
            TOMLSerializer(),
            RDFSerializer(),
        ]
        for serializer in tmp_serializers:
            for ext in serializer.extensions():
                self._serializers[ext] = serializer


class DeserializerFactory():

    def __init__(self, **kwargs) -> None:
        self._deserializers: dict[str, Deserializer] = {}
        self._init_deserializer(**kwargs)

    def deserialize(self,
                    suffix: str,
                    serialized: str | bytes,
                    normalizer: Normalizer,
                    enrich: dict | None = None) -> Project:
        deserializer = self._deserializers.get(suffix.lower())
        if not deserializer:
            raise ValueError(f"Unknown deserializer type: '{suffix}'")
        return deserializer.deserialize(serialized, normalizer, enrich)

    def _init_deserializer(self):

        tmp_deserializers = [
            YAMLDeserializer(),
            TOMLDeserializer(),
            RDFDeserializer(),
        ]
        for deserializer in tmp_deserializers:
            for ext in deserializer.extensions():
                self._deserializers[ext] = deserializer
