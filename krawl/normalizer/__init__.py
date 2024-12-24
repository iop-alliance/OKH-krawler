from __future__ import annotations

from html.parser import HTMLParser
from io import StringIO

from langdetect import LangDetectException
from langdetect import detect as detect_language

from krawl.fetcher.result import FetchResult
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
