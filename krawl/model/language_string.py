# SPDX-FileCopyrightText: 2025 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass
# from rdflib import Literal

@dataclass(slots=True, unsafe_hash=True)
class LangStr:
    """Python version of an RDF `^^rdf:langString`, for example `"Hello World"@en`."""
    text: str
    language: str

    # def to_rdf(self) -> Literal:
    #     return Literal(self.text, lang=self.language)
