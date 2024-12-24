from __future__ import annotations

import json
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
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
        match type_:
            case "weak":
                return cls.WEAK
            case "strong":
                return cls.STRONG
            case "permissive":
                return cls.PERMISSIVE
            case _:
                return cls.UNKNOWN


@dataclass(slots=True, frozen=True)
class License:  # pylint: disable=too-many-instance-attributes
    _id: str
    name: str
    type_: LicenseType = LicenseType.UNKNOWN
    reference_url: str = None
    details_url: str = None
    is_spdx: bool = False
    is_osi_approved: bool = False
    is_fsf_libre: bool = False
    is_blocked: bool = True

    def id(self) -> str:
        return self._id

    def __str__(self) -> str:
        return self.id()

    def __repr__(self) -> str:
        return self.id()


def _normalize_name(name: str) -> str:
    return unicodedata.normalize('NFKD', name).casefold().encode('ascii', 'ignore').strip()


def _init_licenses():
    """Load the licenses and blocklist the included assets files.

    The lists originate from:
        spdx-licenses.json: https://raw.githubusercontent.com/spdx/license-list-data/master/json/licenses.json
        spdx-blocklist.json: https://raw.githubusercontent.com/OPEN-NEXT/LOSH-Licenses/main/SPDX-blocklist.json
    """
    assets_path = Path(__file__).parent.parent / "assets"

    licenses_file = assets_path / "spdx-licenses.json"
    with licenses_file.open("r") as f:
        raw_license_info = json.load(f)
        license_info = {_normalize_name(lic["licenseId"]): lic for lic in raw_license_info["licenses"]}
    licenses_extra_file = assets_path / "spdx-licenses-extra.json"
    with licenses_extra_file.open("r") as f:
        raw_license_extra_info = json.load(f)
        license_extra_info = {_normalize_name(lic["licenseId"]): lic for lic in raw_license_extra_info["licenses"]}
    for name in license_extra_info:
        if name in license_info:
            license_info[name] = _merge_dicts(license_info[name], license_extra_info[name])

    licenses = {
        n: License(
            _id=lic_inf["licenseId"],
            name=lic_inf["name"],
            type_=LicenseType.from_string(lic_inf.get("type")),
            reference_url=lic_inf["reference"],
            details_url=lic_inf["detailsUrl"],
            is_spdx=True,
            is_osi_approved=lic_inf["isOsiApproved"],
            is_fsf_libre=lic_inf.get("isFsfLibre", False),
            is_blocked=lic_inf.get("isBlocked", False),
        ) for n, lic_inf in license_info.items()
    }

    # create mapping between license name and id (performance wise)
    name_to_id = {_normalize_name(lic.name): key for key, lic in licenses.items()}

    return licenses, name_to_id


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

    for key, x_val in x.items():
        if isinstance(x_val, Mapping) and key in y:
            merged[key] = _merge_dicts(x_val, y[key])
    return merged


def get_licenses() -> list:
    return list(_licenses.values())


def get_blocked():
    return filter(lambda lic: lic.is_blocked, _licenses.values())


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
    print(f'WARN: Non-SPDX license detected: "{id_or_name}"')

    return License(
        _id=f'LicenseRef-{id_or_name}',
        name=id_or_name,
    )


def get_spdx_by_id_or_name(id_or_name: str) -> str | None:
    spdx_id = None
    license = get_by_id_or_name(id_or_name)
    if license:
        spdx_id = license.id()
    return spdx_id


# preload the license on import
_licenses, _name_to_id = _init_licenses()
