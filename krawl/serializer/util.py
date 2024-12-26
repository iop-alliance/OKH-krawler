from __future__ import annotations

from pathlib import Path

import orjson

from krawl.errors import SerializerError


def _orjson_manual_type_mapper(value) -> str:
    if isinstance(value, Path):
        return str(value)
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
