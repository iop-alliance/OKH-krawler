from __future__ import annotations

from html.parser import HTMLParser
from io import StringIO

from krawl.project import Project


def strip_html(html):

    class HTMLStripper(HTMLParser):

        def __init__(self):
            super().__init__()
            self.reset()
            self.strict = False
            self.convert_charrefs = True
            self.text = StringIO()

        def handle_data(self, d):
            self.text.write(d)

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
