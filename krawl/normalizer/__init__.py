from __future__ import annotations

from html.parser import HTMLParser
from io import StringIO

from langdetect import LangDetectException
from langdetect import detect as detect_language

from krawl.fetcher import FetchResult
from krawl.model.project import Project


def strip_html(html):

    class HTMLStripper(HTMLParser):

        def __init__(self):
            super().__init__()
            self.reset()
            self.strict = False
            self.convert_char_refs = True
            self.text = StringIO()

        def handle_data(self, data):
            self.text.write(data)

        def get_data(self):
            return self.text.getvalue()

    s = HTMLStripper()
    s.feed(html)
    return s.get_data()


class FileHandler:
    """Interface handlers of file references within a project.
    This handing differs between platforms (and in a way - potentially - between projects).
    This is used e.g. in FileHandler.__init__()"""

    def gen_proj_info(self, manifest_raw: dict) -> dict:
        """From the raw manifest data, extracts and generates the essential info
        required by this handler for all its methods steps.

        Args:
            manifest_raw (dict): The raw manifest data.
        """
        raise NotImplementedError()

    def is_frozen_url(self, proj_info: dict, url: str) -> bool:
        """Figures out whether the argument is a frozen or a non-frozen URL
        to a file in the project.

        Args:
            proj_info (dict): The info about the containing OKH project
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
            proj_info (dict): The info about the containing OKH project
            relative_path (str): Should represent either a frozen or non-frozen URL to a file
            # version (str): Should be None or a repo-/project-version specifier (e.g. a git tag or commit ID)
            frozen (bool): Whether the result should be a frozen or a non-frozen URL
        """
        raise NotImplementedError()

    def extract_path(self, proj_info: dict, url: str) -> str:
        """Extracts a project-/repo-relative path from a file reference URL.

        Args:
            proj_info (dict): The info about the containing OKH project
            url (str): Should represent either a frozen or non-frozen URL to a file
        """
        raise NotImplementedError()


class Normalizer:
    """Interface for normalizing metadata fields
    according to the OKH specification."""

    def normalize(self, fetch_result: FetchResult) -> Project:
        """Turns raw, fetched data into a normalized form,
        valid under the latest OKH standard.

        Args:
            fetch_result (dict): Fetched data (plus crawling meta data) be normalized
        """
        raise NotImplementedError()

    @classmethod
    def _language(cls, description: str | None) -> str | None:
        if not description:
            return None
        try:
            lang = detect_language(description)
        except LangDetectException:
            return None
        if lang == "unknown":
            return None
        return lang
