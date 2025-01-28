# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""\
Utilities for dictionaries, useful for manifest containing dicts.\
"""

from __future__ import annotations

import re
from datetime import datetime
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
    def to_string_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        if isinstance(value, set):
            value = list(value)
        if isinstance(value, list):
            items: list[str] = []
            for itm in value:
                itm_str = DictUtils.to_string(itm)
                if itm_str:
                    items.append(itm_str)
            return items
        else:
            raise TypeError

    @staticmethod
    def to_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, str):
            datetime_str: str = value
            try:
                return datetime.fromisoformat(datetime_str)
            except Exception:
                return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S%z")
        if isinstance(value, int):
            return datetime.fromtimestamp(value)
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
    def clean_name(value: str) -> str:
        no_special = re.sub('[^0-9a-zA-Z_]', '_', value)
        no_double_underscore = re.sub('__+', '_', no_special)
        trimmed = re.sub('_$', '', re.sub('^_', '', no_double_underscore))
        return trimmed

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
