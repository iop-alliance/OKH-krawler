from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

# NOTE We do this strange typing hackery to avoid circular imports
_DataSet: TypeAlias = object
_Manifest: TypeAlias = object


@dataclass(slots=True, frozen=True)
class FetchResult:
    """The result of a successful fetch of an OSH projects meta-data.
    This might be OKH data, or projects hosting systems native format
    (e.g. whatever the Thingiverse API returns about a project;
    probably in JSON format)."""
    data_set: _DataSet = None  # Meta-data about the crawl
    data: _Manifest = None  # The actually main content of the crawl; yummy, yummy data!


# pylint: disable=wrong-import-position
from krawl.model.data_set import DataSet
from krawl.model.manifest import Manifest

_DataSet: TypeAlias = DataSet
_Manifest: TypeAlias = Manifest
