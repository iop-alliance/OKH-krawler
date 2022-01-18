from __future__ import annotations

from pathlib import Path

from krawl.cli.command import KrawlCommand
from krawl.serializer.rdf import RDFProjectSerializer
from krawl.serializer.toml import TOMLProjectSerializer
from krawl.serializer.yaml import YAMLProjectSerializer
from krawl.validator.strict import StrictValidator


class ValidateManifestCommand(KrawlCommand):
    """Validate a given manifest file.

    manifest
        {file : Manifest file to validate}
        {--q|quiet : Do not print reasons in case of invalid manifest}
    """

    def handle(self):
        path = Path(self.argument("file"))
        quiet = self.option("quiet")

        if not path.exists():
            raise FileNotFoundError(f"'{path}' doesn't exist")
        if not path.is_file():
            raise OSError(f"'{path}' is not a file")

        # parse manifest file
        suffix = path.suffix.lower()
        if suffix in [".yml", ".yaml"]:
            serializer = YAMLProjectSerializer()
        elif suffix == ".toml":
            serializer = TOMLProjectSerializer()
        elif suffix == ".ttl":
            raise Exception("Turtle RDF can currently not be validated")
            serializer = RDFProjectSerializer()
        else:
            raise Exception(f"Unknown file type '{suffix}'")
        with path.open("r") as f:
            content = f.read()
        project = serializer.deserialize(content)

        # validate manifest
        validator = StrictValidator()
        ok, reasons = validator.validate(project)
        if not ok:
            if not quiet:
                for r in reasons:
                    self.line(r)
            return 1

        return 0
