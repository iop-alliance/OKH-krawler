from __future__ import annotations

import json
import unicodedata
from pathlib import Path

_licenses = None
_name_to_id = None


class License:

    __slots__ = [
        "_id", "_name", "_reference", "_details", "_is_spdx", "_is_osi_approved", "_is_fsf_libre", "_is_blocked"
    ]

    def __init__(
        self,
        id,
        name,
        reference,
        details,
        is_spdx,
        is_osi_approved,
        is_fsf_libre,
        is_blocked,
    ):
        self._id = id
        self._name = name
        self._reference = reference
        self._details = details
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
    def reference(self):
        return self._reference

    @property
    def details(self):
        return self._details

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

    blocklist_file = assets_path / "spdx-blocklist.json"
    with blocklist_file.open("r") as f:
        blocked = {_normalize_name(l["licenseId"]) for l in json.load(f)}

    licenses_file = assets_path / "spdx-licenses.json"
    with licenses_file.open("r") as f:
        raw_license_info = json.load(f)
    _licenses = {
        _normalize_name(l["licenseId"]): License(
            id=l["licenseId"],
            name=l["name"],
            reference=l["reference"],
            details=l["detailsUrl"],
            is_spdx=True,
            is_osi_approved=l["isOsiApproved"],
            is_fsf_libre=l.get("isFsfLibre", False),
            is_blocked=l["name"] in blocked,
        ) for l in raw_license_info["licenses"]
    }

    # create mapping between license name and id (performance wise)
    _name_to_id = {_normalize_name(l.name): k for k, l in _licenses.items()}


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
