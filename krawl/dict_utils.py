"""\
Utilities for dictionaries, useful for manifest containing dicts.\
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class DictUtils:

    @staticmethod
    def get_key(obj, *key, default=None):
        last = obj
        for k in key:
            if not last or k not in last:
                return default
            last = last[k]
        if not last:
            return default
        return last

    @staticmethod
    def to_string(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            return str(value)
        return None

    @staticmethod
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

    @staticmethod
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

    # HACK If this method is called `to_path`, it will be overwritten by some PosixPath ... -> Python!
    @staticmethod
    def to_path(value: Any) -> Path | None:
        # print(f"to_path - 1: {type(value)} - '{value}'")
        if value is None:
            return None
        if isinstance(value, Path):
            return value
        value = DictUtils.to_string(value)
        # print(f"to_path - 2: {type(value)} - '{value}'")
        if value:
            return Path(value)
        return None

    @staticmethod
    def clean_name(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            no_special = re.sub('[^0-9a-zA-Z_]', '_', value)
            no_double_underscore = re.sub('__+', '_', no_special)
            trimmed = re.sub('_$', '', re.sub('^_', '', no_double_underscore))
            return trimmed
        return None

    @staticmethod
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
