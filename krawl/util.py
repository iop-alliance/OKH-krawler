from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

import validators


def slugify(value):
    """Convert a string to a slug representation.

    Args:
        value (str): The string value to be slug-ified.

    Returns:
        str: A slug representation of the string.

    Examples:
        {{ 'Hello World' | slugify() }} -> 'hello-world'
    """
    value = unicodedata.normalize("NFKC", str(value))
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


def is_url(str: str) -> bool:
    """Figures out whether the argument is a valid URL.

    Args:
        str (str): Any kind of string
    """
    return validators.url(str)


def extract_path(url: str) -> str:
    """Extracts the path part from a URL.

    Args:
        url (str): A regular URL
    """
    parsed_url = urlparse(url)
    return parsed_url.path
