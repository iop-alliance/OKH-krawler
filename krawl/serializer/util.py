# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import orjson

from krawl.errors import SerializerError

RE_DOI = re.compile("^(doi: |DOI: |https://doi.org/)?10\\.\\d{4,9}\\/[-._;()/:a-zA-Z0-9]+$")


def _orjson_manual_type_mapper(value) -> str:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, set):
        value = list(value)
        value.sort()
        return value
    raise TypeError


def json_serialize(obj) -> str:
    try:
        # pylint: disable=no-member
        serialized = orjson.dumps(obj,
                                  default=_orjson_manual_type_mapper,
                                  option=orjson.OPT_NAIVE_UTC | orjson.OPT_APPEND_NEWLINE | orjson.OPT_INDENT_2 |
                                  orjson.OPT_SORT_KEYS).decode("utf-8")
    except Exception as err:
        raise SerializerError(f"failed to serialize JSON: {err}") from err
    return serialized


def is_doi(value: str) -> bool:
    """Checks if the given string is a valid DOI identifier.

    Examples:

    - https://doi.org/10.1080/10509585.2015.1092083
    - 10.1080/10509585.2015.1092083
    - doi: 10.1080/10509585.2015.1092083
    - DOI: 10.1080/10509585.2015.1092083"""
    return bool(RE_DOI.match(value))


def is_web_url(value: str) -> bool:
    parsed_url = urlparse(value)
    return parsed_url.scheme in ('http', 'https')
