from __future__ import annotations

import json
import unicodedata
from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import Any

_licenses = None
_name_to_id = None


class LicenseType(str, Enum):
    UNKNOWN = "unknown"
    WEAK = "weak"
    STRONG = "strong"
    PERMISSIVE = "permissive"

    def __str__(self) -> str:
        return self.name

    @classmethod
    def from_string(cls, type_: str):
        type_ = type_ or "unknown"
        type_ = type_.lower()
        if type_ == "weak":
            return cls.WEAK
        elif type_ == "strong":
            return cls.STRONG
        elif type_ == "permissive":
            return cls.PERMISSIVE
        else:
            return cls.UNKNOWN


class License:

    __slots__ = [
        "_id", "_name", "_type", "_reference_url", "_details_url", "_is_spdx", "_is_osi_approved", "_is_fsf_libre",
        "_is_blocked"
    ]

    def __init__(
        self,
        id,
        name,
        type_,
        reference_url,
        details_url,
        is_spdx,
        is_osi_approved,
        is_fsf_libre,
        is_blocked,
    ):
        self._id = id
        self._name = name
        self._type: LicenseType = type_
        self._reference_url = reference_url
        self._details_url = details_url
        self._is_spdx = is_spdx
        self._is_osi_approved = is_osi_approved
        self._is_fsf_libre = is_fsf_libre
        self._is_blocked = is_blocked

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def type(self):
        return self._type

    @property
    def reference_url(self):
        return self._reference_url

    @property
    def details_url(self):
        return self._details_url

    @property
    def is_spdx(self):
        return self._is_spdx

    @property
    def is_osi_approved(self):
        return self._is_osi_approved

    @property
    def is_fsf_libre(self):
        return self._is_fsf_libre

    @property
    def is_blocked(self):
        return self._is_blocked

    def __str__(self) -> str:
        return self._id

    def __repr__(self) -> str:
        return self._id


def _normalize_name(name: str) -> str:
    return unicodedata.normalize('NFKD', name).casefold().encode('ascii', 'ignore').strip()


def _init_licenses():
    """Load the licenses and blocklist the included assets files.

    The lists originate from:
        spdx-licenses.json: https://raw.githubusercontent.com/spdx/license-list-data/master/json/licenses.json
        spdx-blocklist.json: https://raw.githubusercontent.com/OPEN-NEXT/LOSH-Licenses/main/SPDX-blocklist.json
    """
    global _licenses, _name_to_id
    assets_path = Path(__file__).parent / "assets"

    licenses_file = assets_path / "spdx-licenses.json"
    with licenses_file.open("r") as f:
        raw_license_info = json.load(f)
        license_info = {_normalize_name(l["licenseId"]): l for l in raw_license_info["licenses"]}
    licenses_extra_file = assets_path / "spdx-licenses-extra.json"
    with licenses_extra_file.open("r") as f:
        raw_license_extra_info = json.load(f)
        license_extra_info = {_normalize_name(l["licenseId"]): l for l in raw_license_extra_info["licenses"]}
    for name in license_extra_info:
        if name in license_info:
            license_info[name] = _merge_dicts(license_info[name], license_extra_info[name])

    _licenses = {
        n: License(
            id=l["licenseId"],
            name=l["name"],
            type_=LicenseType.from_string(l.get("type")),
            reference_url=l["reference"],
            details_url=l["detailsUrl"],
            is_spdx=True,
            is_osi_approved=l["isOsiApproved"],
            is_fsf_libre=l.get("isFsfLibre", False),
            is_blocked=l.get("isBlocked", False),
        ) for n, l in license_info.items()
    }

    # create mapping between license name and id (performance wise)
    _name_to_id = {_normalize_name(l.name): k for k, l in _licenses.items()}


def _merge_dicts(x: Mapping[Any, Any], y: Mapping[Any, Any]) -> dict[Any, Any]:
    """Recursively merges two dicts.

    When keys exist in both the value of 'y' is used.

    Args:
        x (dict): First dict
        y (dict): Second dict

    Returns:
        dict: The merged dict
    """
    assert isinstance(x, Mapping) and isinstance(y, Mapping)

    merged = dict(x, **y)
    xkeys = x.keys()

    for key in xkeys:
        if isinstance(x[key], Mapping) and key in y:
            merged[key] = _merge_dicts(x[key], y[key])
    return merged


def get_licenses() -> list:
    return list(_licenses.values())


def get_blocked():
    return [l for l in _licenses.values() if not l.is_blocked]


def get_by_id(id: str) -> License:
    normalized = _normalize_name(id)
    if normalized in _licenses:
        return _licenses[normalized]
    return None


def get_by_id_or_name(id_or_name: str) -> License:
    if not id_or_name:
        return None
    normalized = _normalize_name(id_or_name)
    if normalized in _licenses:
        return _licenses[normalized]
    if normalized in _name_to_id:
        return _licenses[_name_to_id[normalized]]
    return None


# preload the license on import
_init_licenses()
