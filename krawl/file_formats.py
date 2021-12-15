from __future__ import annotations

from csv import DictReader
from pathlib import Path

_formats = {}


class FileFormat:

    def __init__(self, type_, extension, category=None):
        self.type = type_
        self.extension = extension if extension.startswith(".") else "." + extension
        self.category = category if category in ["source", "export"] else None

    def __str__(self) -> str:
        return f"(type: {self.type}, extension: {self.extension}, category: {self.category}"

    def __repr__(self) -> str:
        return str(self)


def _init_file_formats():
    """Load the file formats from the included assets files.

    The lists originate from:
        - https://gitlab.com/OSEGermany/osh-tool/-/tree/master/data
        - https://github.com/hoijui/file-extension-list
    """
    global _formats

    assets_path = Path(__file__).parent / "assets" / "file_extensions"
    # load file formats from txt
    txt_files = [
        "code",
        "image",
        "sheet",
        "text",
    ]
    for name in txt_files:
        path = assets_path / (name + ".txt")
        with path.open("r") as f:
            extensions = f.read().splitlines()
            _formats[name] = {f".{e}": FileFormat(name, e) for e in extensions}

    # load file formats from csv
    csv_files = [
        "cad",
        "pcb",
    ]
    for name in csv_files:
        path = assets_path / (name + ".csv")
        with path.open("r") as f:
            csv_reader = DictReader(f)
            _formats[name] = {f".{r['extension']}": FileFormat(name, r["extension"], r["category"]) for r in csv_reader}


def get_formats(type_):
    if not type_ in _formats:
        raise Exception(f"no such file format '{type_}'")
    return _formats[type_]


# preload the file formats on import
_init_file_formats()
