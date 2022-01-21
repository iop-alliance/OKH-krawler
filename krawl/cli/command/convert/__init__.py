from __future__ import annotations

from pathlib import Path

from krawl.cli.command import KrawlCommand
from krawl.errors import DeserializerError
from krawl.fetcher.util import is_binary, is_empty
from krawl.normalizer.manifest import ManifestNormalizer
from krawl.serializer.json_deserializer import JSONProjectDeserializer
from krawl.serializer.json_serializer import JSONProjectSerializer
from krawl.serializer.rdf_deserializer import RDFProjectDeserializer
from krawl.serializer.rdf_serializer import RDFProjectSerializer
from krawl.serializer.toml_deserializer import TOMLProjectDeserializer
from krawl.serializer.toml_serializer import TOMLProjectSerializer
from krawl.serializer.yaml_deserializer import YAMLProjectDeserializer
from krawl.serializer.yaml_serializer import YAMLProjectSerializer


class ConvertManifestCommand(KrawlCommand):
    """Convert and sanitize a given manifest file. Supported formats: TOML, YAML, JSON, RDF

    convert
        {from : Manifest file to convert}
        {to : Destination file}
        {--f|force : Force overwrite of an existing file}
    """

    def handle(self):
        convert_from = Path(self.argument("from"))
        convert_to = Path(self.argument("to"))
        force = self.option("force")

        if not convert_from.exists():
            raise FileNotFoundError(f"'{convert_from}' doesn't exist")
        if not convert_from.is_file():
            raise OSError(f"'{convert_from}' is not a file")

        if convert_to.exists():
            if not convert_to.is_file():
                raise OSError(f"'{convert_to}' exists and is not a file")
            if not force:
                raise FileExistsError(f"'{convert_to}' already exists, use 'force' to overwrite")

        # deserialize project in different format
        suffix = convert_from.suffix.lower()
        if suffix in [".yml", ".yaml"]:
            deserializer = YAMLProjectDeserializer()
        elif suffix == ".toml":
            deserializer = TOMLProjectDeserializer()
        elif suffix == ".toml":
            deserializer = TOMLProjectDeserializer()
        elif suffix == ".json":
            deserializer = JSONProjectDeserializer()
        elif suffix == ".ttl":
            raise Exception("Turtle RDF can currently not be converted into a different format")
            # deserializer = RDFProjectDeserializer()
        else:
            raise Exception(f"Unknown file type '{suffix}'")

        content = convert_from.read_text()
        if is_empty(content) or is_binary(content):
            raise DeserializerError("invalide file content")
        normalizer = ManifestNormalizer()
        project = deserializer.deserialize(content, normalizer)

        # serialize project in different format
        suffix = convert_to.suffix.lower()
        if suffix in [".yml", ".yaml"]:
            serializer = YAMLProjectSerializer()
        elif suffix == ".toml":
            serializer = TOMLProjectSerializer()
        elif suffix == ".toml":
            serializer = TOMLProjectSerializer()
        elif suffix == ".json":
            serializer = JSONProjectSerializer()
        elif suffix == ".ttl":
            serializer = RDFProjectSerializer()
        else:
            raise Exception(f"Unknown file type '{suffix}'")

        serialized = serializer.serialize(project)
        convert_to.write_text(serialized)

        return 0
