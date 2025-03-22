# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass

from krawl.model.data_set import DataSet
from krawl.model.manifest import Manifest


@dataclass(slots=True, frozen=True)
class FetchResult:
    """The result of a successful fetch of an OSH projects meta-data.
    This might be OKH data, or projects hosting systems native format
    (e.g. whatever the Thingiverse API returns about a project;
    probably in JSON format)."""
    data_set: DataSet
    """Meta-data about the crawl"""
    data: Manifest
    """The main content of the crawl; yummy, yummy data!"""
