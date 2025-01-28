# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2022 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

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
    def _clean_language(cls, raw_lang: list[str] | str | None) -> list[str]:
        langs: list[str] = []
        if not raw_lang:
            return langs
        if isinstance(raw_lang, str):
            return [raw_lang]
        if isinstance(raw_lang, list):
            return raw_lang
        else:
            raise TypeError(f"Expected list or str, got {type(raw_lang)}")

    @classmethod
    def _language_from_description(cls, description: str | None) -> list[str]:
        langs: list[str] = []
        if not description:
            return langs
        try:
            lang = detect_language(description)
            if lang == "unknown":
                return langs
            else:
                langs.append(lang)
        except LangDetectException:
            return langs
        return langs
