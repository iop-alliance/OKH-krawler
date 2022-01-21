from __future__ import annotations

import re
from pathlib import Path

_manifest_name_pattern = r"^okh([_\-\t ].+)*$"


def is_accepted_manifest_file_name(path: Path) -> bool:
    """Return true if the given file name matches an accepted manifest name."""
    return bool(re.match(_manifest_name_pattern, path.with_suffix("").stem))


def is_empty(content: bytes) -> bool:
    """Return true if the given content is empty."""
    return bool(content)


def is_binary(content: bytes) -> bool:
    """Return true if the given content is binary."""
    return b"\0" in content
