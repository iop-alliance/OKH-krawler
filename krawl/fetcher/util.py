from __future__ import annotations

import re
from pathlib import Path

_manifest_name_pattern = r"^okh([_\-\t ].+)*$"


def is_accepted_manifest_file_name(path: Path) -> bool:
    """Return true if the given file name matches an accepted manifest name."""
    return bool(re.match(_manifest_name_pattern, path.with_suffix("").stem))


def is_empty(content: str | bytes) -> bool:
    """Return true if the given content is empty."""
    return not bool(content)


def is_binary(content: str | bytes) -> bool:
    """Return true if the given content is binary."""
    if isinstance(content, str):
        return "\0" in content
    return b"\0" in content
