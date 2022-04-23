from __future__ import annotations

from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
from typing import Any
import re

from krawl.project import Project


def strip_html(html):

    class HTMLStripper(HTMLParser):

        def __init__(self):
            super().__init__()
            self.reset()
            self.strict = False
            self.convert_charrefs = True
            self.text = StringIO()

        def handle_data(self, data):
            self.text.write(data)

        def get_data(self):
            return self.text.getvalue()

    s = HTMLStripper()
    s.feed(html)
    return s.get_data()


class Normalizer:
    """Interface for normalizing metadata fields according to the OKH-LOSH
specification."""

    def normalize(self, raw: dict) -> Project:
        """Turns projects metadata into a normalized form that can be easily
        processed by the program.

        Args:
            raw (dict): Raw project metadata to be normalized
        """
        raise NotImplementedError()

    @staticmethod
    def _get_key(obj, *key, default=None):
        last = obj
        for k in key:
            if not last or k not in last:
                return default
            last = last[k]
        if not last:
            return default
        return last

    @classmethod
    def _string(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            return str(value)
        return None

    @classmethod
    def _float(cls, value: Any) -> float | None:
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

    @classmethod
    def _int(cls, value: Any) -> int | None:
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

    @classmethod
    def _path(cls, value: Any) -> Path | None:
        if value is None:
            return None
        if isinstance(value, Path):
            return value
        value = cls._string(value)
        if value:
            return Path(value)
        return None

    @classmethod
    def _clean_name(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            no_special = re.sub('[^0-9a-zA-Z_]', '_', value)
            no_double_underscore = re.sub('__+', '_', no_special)
            trimmed = re.sub('_$', '', re.sub('^_', '', no_double_underscore))
            return trimmed
        return None

    @classmethod
    def _ensure_unique_clean_names(cls, parts: list):
        uniques = []
        for part in parts:
            if part.name_clean is not None:
                base = part.name_clean
                cnt = 1
                while part.name_clean in uniques:
                    part.name_clean = base + str(cnt)
                    cnt += 1
                uniques.append(part.name_clean)
