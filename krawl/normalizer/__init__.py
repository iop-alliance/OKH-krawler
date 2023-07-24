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


class DictUtils:
    """Utilities for dictionaries, useful for manifest containing dicts."""

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


class FileHandler:
    """Interface handlers of file references within a project.
    This handing differs between platforms (and in a way - potentially - between projects).
    This is used e.g. in FileHandler.__init__()"""

    def gen_proj_info(self, manifest_raw: dict) -> dict:
        """From the raw manifest data, extracts and generates the essential info
        requried by this handler for all its methods steps.

        Args:
            manifest_raw (dict): The raw manifest data.
        """
        raise NotImplementedError()

    def is_frozen_url(self, proj_info: dict, url: str) -> bool:
        """Figures out whether the argument is a frozen or a non-frozen URL
        to a file in the project.

        Args:
            url (str): Should represent either a frozen or non-frozen URL to a file within the project/repo
        """
        raise NotImplementedError()

    # NOTE version, just like project slug, should be given to the constructor of this FileHandler
    # def to_url(self, relative_path: str, version: str = None) -> bool:
    def to_url(self, proj_info: dict, relative_path: str, frozen: bool) -> str:
        """Constructs a URL from a relative-path to a file,
        either a non-frozen one if version  is None,
        or a frozen one otherwise.

        Args:
            relative_path (str): Should represent either a frozen or non-frozen URL to a file
            # version (str): Should be None or a repo-/project-version specifier (e.g. a git tag or commit ID)
            frozen (bool): Whether the result should be a frozen or a non-frozen URL
        """
        raise NotImplementedError()

    def extract_path(self, proj_info: dict, url: str) -> str:
        """Extracts a project-/repo-relative path from a file reference URL.

        Args:
            url (str): Should represent either a frozen or non-frozen URL to a file
        """
        raise NotImplementedError()


class Normalizer(DictUtils):
    """Interface for normalizing metadata fields according to the OKH-LOSH
specification."""

    def normalize(self, raw: dict) -> Project:
        """Turns projects metadata into a normalized form that can be easily
        processed by the program.

        Args:
            raw (dict): Raw project metadata to be normalized
        """
        raise NotImplementedError()
