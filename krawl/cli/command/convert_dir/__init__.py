from __future__ import annotations

import re
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


class ConvertDirManifestCommand(KrawlCommand):
    """Convert and sanitize all files in a dir that match a given extension - recursively - to the format of the second extension provided. Supported formats: TOML, YAML, JSON, RDF

    convdir
        {dir : Root dir to scan}
        {from : Manifest file extension to look for}
        {to : Destination file extension}
        {--f|force : Force overwrite of a existing files}
    """

    def handle(self):
        convert_dir = Path(self.argument("dir"))
        ext_from = self.argument("from")
        ext_to = self.argument("to")
        force = self.option("force")

        if not convert_dir.exists():
            raise FileNotFoundError(f"'{convert_dir}' does not exist")
        if not convert_dir.is_dir():
            raise OSError(f"'{convert_dir}' is not a directory")

        # deserialize project in different format
        ext_lower_from = ext_from.lower()
        if ext_lower_from in [".yml", ".yaml"]:
            deserializer = YAMLProjectDeserializer()
        elif ext_lower_from == ".toml":
            deserializer = TOMLProjectDeserializer()
        elif ext_lower_from == ".toml":
            deserializer = TOMLProjectDeserializer()
        elif ext_lower_from == ".json":
            deserializer = JSONProjectDeserializer()
        elif ext_lower_from == ".ttl":
            raise Exception("Turtle RDF can currently not be converted into a different format")
            # deserializer = RDFProjectDeserializer()
        else:
            raise Exception(f"Unknown file type '{ext_lower_from}'")

        # serialize project in different format
        ext_lower_to = ext_to.lower()
        if ext_lower_to in [".yml", ".yaml"]:
            serializer = YAMLProjectSerializer()
        elif ext_lower_to == ".toml":
            serializer = TOMLProjectSerializer()
        elif ext_lower_to == ".toml":
            serializer = TOMLProjectSerializer()
        elif ext_lower_to == ".json":
            serializer = JSONProjectSerializer()
        elif ext_lower_to == ".ttl":
            serializer = RDFProjectSerializer()
        else:
            raise Exception(f"Unknown file type '{ext_lower_to}'")

        input_files = []
        for inf in Path(convert_dir).rglob(f'*%s' % ext_from):
            if inf.is_file():
                input_files.append(inf)

        if_count = len(input_files)
        if_no = 0
        for input_file_path in input_files:
            if_no = if_no + 1
            convert_from = str(input_file_path)
            convert_to = re.sub(r'\%s$' % ext_from, ext_to, convert_from)

            convert_from_path = Path(convert_from)
            convert_to_path = Path(convert_to)

            if convert_to_path.exists():
                if not convert_to_path.is_file():
                    raise OSError(f"'{convert_to_path}' exists and is not a file")
                if not force:
                    print(f"'{convert_to_path}' already exists, use 'force' to overwrite")
                    continue

            print("    %d/%d '%s' -> '%s' ..." % (if_no, if_count, convert_from, convert_to))
            content = convert_from_path.read_text()
            if is_empty(content) or is_binary(content):
                raise DeserializerError("invalid file content in '%s'" % convert_from)
            normalizer = ManifestNormalizer()
            project = deserializer.deserialize(content, normalizer)

            serialized = serializer.serialize(project)
            convert_to_path.write_text(serialized)

        return 0
