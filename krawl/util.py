from __future__ import annotations

import re
import unicodedata


def slugify(value):
    """Convert a string to a slug representation.

    Args:
        value (str): The string value to be slugified.

    Returns:
        str: A slug representation of the string.

    Examples:
        {{ 'Hello World' | slugify() }} -> 'hello-world'
    """
    value = unicodedata.normalize("NFKC", str(value))
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")
