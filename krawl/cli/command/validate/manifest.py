from __future__ import annotations

from pathlib import Path

from krawl.cli.command import KrawlCommand
from krawl.normalizer.manifest import ManifestNormalizer
from krawl.serializer.json_deserializer import JSONProjectDeserializer
from krawl.serializer.rdf_deserializer import RDFProjectDeserializer
from krawl.serializer.toml_deserializer import TOMLProjectDeserializer
from krawl.serializer.yaml_deserializer import YAMLProjectDeserializer
from krawl.validator.strict import StrictValidator


class ValidateManifestCommand(KrawlCommand):
    """Validate a given manifest file. Non-zero return codes indicate an error.

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
            deserializer = YAMLProjectDeserializer()
        elif suffix == ".toml":
            deserializer = TOMLProjectDeserializer()
        elif suffix == ".json":
            deserializer = JSONProjectDeserializer()
        elif suffix == ".ttl":
            raise Exception("Turtle RDF can currently not be validated")
            # deserializer = RDFProjectDeserializer()
        else:
            raise Exception(f"Unknown file type '{suffix}'")
        with path.open("r") as f:
            content = f.read()
        normalizer = ManifestNormalizer()
        project = deserializer.deserialize(content, normalizer)

        # validate manifest
        validator = StrictValidator()
        ok, reasons = validator.validate(project)
        if not ok:
            if not quiet:
                for r in reasons:
                    self.line(r)
            return 1

        return 0
