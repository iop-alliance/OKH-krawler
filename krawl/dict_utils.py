"""\
Utilities for dictionaries, useful for manifest containing dicts.\
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def get_key(obj, *key, default=None):
    last = obj
    for k in key:
        if not last or k not in last:
            return default
        last = last[k]
    if not last:
        return default
    return last


def to_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    return None


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, float):
        return value
    if isinstance(value, (str, int)):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, (str, float)):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def to_path(value: Any) -> Path | None:
    if value is None:
        return None
    if isinstance(value, Path):
        return value
    value = to_string(value)
    if value:
        return Path(value)
    return None


def clean_name(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        no_special = re.sub('[^0-9a-zA-Z_]', '_', value)
        no_double_underscore = re.sub('__+', '_', no_special)
        trimmed = re.sub('_$', '', re.sub('^_', '', no_double_underscore))
        return trimmed
    return None


def ensure_unique_clean_names(parts: list):
    uniques = []
    for part in parts:
        if part.name_clean is not None:
            base = part.name_clean
            cnt = 1
            while part.name_clean in uniques:
                part.name_clean = base + str(cnt)
                cnt += 1
            uniques.append(part.name_clean)
