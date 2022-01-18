from __future__ import annotations

from pathlib import Path

from krawl.cli.command import KrawlCommand
from krawl.serializer.rdf import RDFProjectSerializer
from krawl.serializer.toml import TOMLProjectSerializer
from krawl.serializer.yaml import YAMLProjectSerializer


class ConvertManifestCommand(KrawlCommand):
    """Convert and sanitize a given manifest file.

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

        # parse manifest file
        suffix = convert_from.suffix.lower()
        if suffix in [".yml", ".yaml"]:
            serializer = YAMLProjectSerializer()
        elif suffix == ".toml":
            serializer = TOMLProjectSerializer()
        elif suffix == ".ttl":
            raise Exception("Turtle RDF can currently not be converted into a different format")
            serializer = RDFProjectSerializer()
        else:
            raise Exception(f"Unknown file type '{suffix}'")
        with convert_from.open("r") as f:
            content = f.read()
        project = serializer.deserialize(content)

        # serialize project in different format
        suffix = convert_to.suffix.lower()
        if suffix in [".yml", ".yaml"]:
            serializer = YAMLProjectSerializer()
        elif suffix == ".toml":
            serializer = TOMLProjectSerializer()
        elif suffix == ".ttl":
            serializer = RDFProjectSerializer()
        else:
            raise Exception(f"Unknown file type '{suffix}'")
        serialized = serializer.serialize(project)
        convert_to.write_text(serialized)

        return 0
