# SPDX-FileCopyrightText: 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2023 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import re
import unicodedata
import urllib.parse
from pathlib import Path

import validators
from ftfy import fix_encoding

_p_space = re.compile('[ \t\r\n]+')


def clean_path(orig_path: Path) -> Path:
    clean_parts: list[str] = []
    for part in orig_path.parts:
        part_clean: str
        if False:
            part_clean = _p_space.sub('_', part)
        else:
            part_clean = url_encode(part)
        clean_parts.append(part_clean)
    return Path(*clean_parts)


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


def extract_path(url: str) -> Path | None:
    """Extracts the path part from a URL.

    Args:
        url (str): A regular URL
    """
    parsed_url = urllib.parse.urlparse(url)
    return Path(parsed_url.path) if parsed_url.path else None


def path_opt(path_part: Path | str | None) -> str:
    return "/" + str(path_part) if path_part else ""


def fix_str_encoding(potentially_bad_str: str) -> str:
    return fix_encoding(potentially_bad_str)


def url_encode(raw_url_part: str) -> str:
    return urllib.parse.quote_plus(raw_url_part)
